from __future__ import annotations

import csv
import statistics
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np

HALF_LIFE_GAMES = 8.0
DEFENSE_SHRINK_GAMES = 10.0
PRIOR_SEASON_WEIGHT = 0.5
MIN_GAMES_FOR_SEASON_SCALE = 40
RECENT_CUSHION_GAMES = 4
CALIBRATION_BUCKETS = 10
BACKTEST_MIN_HISTORY = 3
COUNT_PRIOR_GAMES = 8.0
COUNT_OPPONENT_ADJUST = False


@dataclass(frozen=True)
class ReceiverGame:
    season: int
    week: int
    player_id: str
    team: str
    opponent: str
    targets: float
    receptions: float
    yards: float
    tds: float


@dataclass(frozen=True)
class SeasonScale:
    targets: float
    rates: dict[str, float]


@dataclass(frozen=True)
class StatSpec:
    key: str
    value: Callable[[ReceiverGame], float]
    kind: str
    thresholds: tuple[int, ...]
    min_bandwidth: float
    level_correction: float
    line_max: int


STATS: dict[str, StatSpec] = {
    "rec_yards": StatSpec(
        key="rec_yards",
        value=lambda g: g.yards,
        kind="continuous",
        thresholds=(20, 40, 60, 80, 100),
        min_bandwidth=14.0,
        level_correction=0.95,
        line_max=150,
    ),
    "receptions": StatSpec(
        key="receptions",
        value=lambda g: g.receptions,
        kind="continuous",
        thresholds=(3, 5, 7, 9),
        min_bandwidth=1.0,
        level_correction=0.95,
        line_max=20,
    ),
    "rec_tds": StatSpec(
        key="rec_tds",
        value=lambda g: g.tds,
        kind="count",
        thresholds=(1, 2),
        min_bandwidth=0.0,
        level_correction=1.0,
        line_max=5,
    ),
}


def load_receiver_games(data_dir: Path, seasons: range) -> list[ReceiverGame]:
    rows: dict[tuple[int, int, str], ReceiverGame] = {}
    for season in seasons:
        path = data_dir / f"player_stats_{season}.csv"
        if not path.exists():
            continue
        with path.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["season_type"] != "REG" or r["position"] not in ("WR", "TE"):
                    continue
                targets = float(r["targets"] or 0)
                if targets <= 0:
                    continue
                game = ReceiverGame(
                    season=int(r["season"]),
                    week=int(r["week"]),
                    player_id=r["player_id"],
                    team=r["team"],
                    opponent=r["opponent_team"],
                    targets=targets,
                    receptions=float(r["receptions"] or 0),
                    yards=float(r["receiving_yards"] or 0),
                    tds=float(r["receiving_tds"] or 0),
                )
                rows[(game.season, game.week, game.player_id)] = game
    return list(rows.values())


def load_cushions(nextgen_dir: Path, seasons: range) -> dict[tuple[int, int, str], float]:
    cushions: dict[tuple[int, int, str], float] = {}
    for season in seasons:
        path = nextgen_dir / f"nextgen_stats_receiving_{season}.csv"
        if not path.exists():
            continue
        with path.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["season_type"] != "REG" or not r["avg_cushion"]:
                    continue
                cushions[(int(r["season"]), int(r["week"]), r["player_gsis_id"])] = float(r["avg_cushion"])
    return cushions


def _scale(rows: list[ReceiverGame]) -> SeasonScale:
    total_targets = sum(g.targets for g in rows)
    rates = {
        key: sum(spec.value(g) for g in rows) / total_targets
        for key, spec in STATS.items()
    }
    return SeasonScale(targets=total_targets / len(rows), rates=rates)


class PredictionContext:
    """Everything knowable before (season, week) kicks off, and nothing after."""

    def __init__(
        self,
        games: list[ReceiverGame],
        season: int,
        week: int,
        stat: str = "rec_yards",
        cushions: dict[tuple[int, int, str], float] | None = None,
        cushion_beta: float = 0.0,
    ) -> None:
        self.season = season
        self.stat = stat
        self.spec = STATS[stat]
        self.cushions = cushions or {}
        self.cushion_beta = cushion_beta
        history = [g for g in games if (g.season, g.week) < (season, week)]

        by_season: dict[int, list[ReceiverGame]] = defaultdict(list)
        for g in games:
            if g.season < season:
                by_season[g.season].append(g)
        self.scales: dict[int, SeasonScale] = {s: _scale(rows) for s, rows in by_season.items()}

        current = [g for g in history if g.season == season]
        if len(current) >= MIN_GAMES_FOR_SEASON_SCALE or season - 1 not in self.scales:
            self.scales[season] = _scale(current) if current else _scale(history)
        else:
            self.scales[season] = self.scales[season - 1]

        prior_cushions = [v for (s, _, _), v in self.cushions.items() if s < season]
        self.cushion_mean = statistics.fmean(prior_cushions) if prior_cushions else 0.0
        self.cushion_sd = statistics.pstdev(prior_cushions) if len(prior_cushions) > 1 else 1.0

        allowed_sum: dict[str, float] = defaultdict(float)
        allowed_weight: dict[str, float] = defaultdict(float)
        for g in history:
            if g.season == season:
                weight = 1.0
            elif g.season == season - 1:
                weight = PRIOR_SEASON_WEIGHT
            else:
                continue
            rate = self.spec.value(g) / g.targets / self.scales[g.season].rates[stat]
            allowed_sum[g.opponent] += weight * rate
            allowed_weight[g.opponent] += weight

        self.defense: dict[str, float] = {}
        for team, weight in allowed_weight.items():
            observed = allowed_sum[team] / weight
            self.defense[team] = (weight * observed + DEFENSE_SHRINK_GAMES) / (weight + DEFENSE_SHRINK_GAMES)

        self.history: dict[str, list[ReceiverGame]] = defaultdict(list)
        for g in sorted(history, key=lambda g: (g.season, g.week)):
            self.history[g.player_id].append(g)

    def _cushion_shift(self, player_id: str) -> float:
        if self.cushion_beta == 0.0:
            return 0.0
        zs = [
            (self.cushions[(g.season, g.week, g.player_id)] - self.cushion_mean) / self.cushion_sd
            for g in self.history.get(player_id, [])
            if (g.season, g.week, g.player_id) in self.cushions
        ]
        if len(zs) < RECENT_CUSHION_GAMES:
            return 0.0
        return statistics.fmean(zs[-RECENT_CUSHION_GAMES:]) - statistics.fmean(zs)

    def predict_samples(self, player_id: str, next_opponent: str) -> tuple[np.ndarray, np.ndarray]:
        hist = self.history.get(player_id, [])
        cur = self.scales[self.season]
        n = len(hist)
        games_ago = np.arange(n)[::-1]
        recency = 0.5 ** (games_ago / HALF_LIFE_GAMES)

        volume = np.array(
            [g.targets / self.scales[g.season].targets * cur.targets for g in hist]
        )
        opp_factor = self.defense.get(next_opponent, 1.0)
        cushion_factor = 1.0 + self.cushion_beta * self._cushion_shift(player_id)
        efficiency = np.array(
            [
                (self.spec.value(g) / g.targets) / self.scales[g.season].rates[self.stat]
                / self.defense.get(g.opponent, 1.0) * opp_factor * cur.rates[self.stat] * cushion_factor
                for g in hist
            ]
        )
        return (
            self.spec.level_correction * np.outer(volume, efficiency).ravel(),
            np.outer(recency, recency).ravel(),
        )

    def predict(self, player_id: str, next_opponent: str) -> tuple[np.ndarray, np.ndarray]:
        if self.spec.kind == "count":
            return self._poisson_rate(player_id, next_opponent)
        return self.predict_samples(player_id, next_opponent)

    def _poisson_rate(self, player_id: str, next_opponent: str) -> tuple[np.ndarray, np.ndarray]:
        cur = self.scales[self.season]
        prior = cur.rates[self.stat] * cur.targets
        hist = self.history.get(player_id, [])
        if hist:
            n = len(hist)
            recency = 0.5 ** (np.arange(n)[::-1] / HALF_LIFE_GAMES)
            vals = np.array([self.spec.value(g) for g in hist])
            rate = ((recency * vals).sum() + COUNT_PRIOR_GAMES * prior) / (recency.sum() + COUNT_PRIOR_GAMES)
        else:
            rate = prior
        if COUNT_OPPONENT_ADJUST:
            rate *= self.defense.get(next_opponent, 1.0)
        return np.array([self.spec.level_correction * rate]), np.array([1.0])

    def raw_samples(self, player_id: str) -> tuple[np.ndarray, np.ndarray]:
        hist = self.history.get(player_id, [])
        return np.array([self.spec.value(g) for g in hist]), np.ones(len(hist))


def prob_at_least(
    values: np.ndarray, weights: np.ndarray, threshold: int, min_bandwidth: float
) -> float:
    total = weights.sum()
    mean = (weights * values).sum() / total
    var = (weights * (values - mean) ** 2).sum() / total
    bandwidth = max(min_bandwidth, 0.25 * var ** 0.5)
    z = (threshold - 0.5 - values) / bandwidth
    upper = 1.0 / (1.0 + np.exp(np.clip(1.702 * z, -700, 700)))
    return float((weights * upper).sum() / total)


def prob_at_least_count(lambdas: np.ndarray, weights: np.ndarray, threshold: int) -> float:
    if threshold <= 0:
        return 1.0
    total = weights.sum()
    term = np.exp(-lambdas)
    cdf = term.copy()
    for k in range(1, threshold):
        term = term * lambdas / k
        cdf += term
    return float((weights * (1.0 - cdf)).sum() / total)


def prob_for_stat(spec: StatSpec, values: np.ndarray, weights: np.ndarray, threshold: int) -> float:
    if spec.kind == "count":
        return prob_at_least_count(values, weights, threshold)
    return prob_at_least(values, weights, threshold, spec.min_bandwidth)


def backtest(
    games: list,
    first: int,
    last: int,
    stat: str = "rec_yards",
    specs: dict[str, StatSpec] | None = None,
    context_cls: type | None = None,
) -> dict:
    specs = specs or STATS
    context_cls = context_cls or PredictionContext
    spec = specs[stat]
    by_week: dict[tuple[int, int], list] = defaultdict(list)
    for g in games:
        by_week[(g.season, g.week)].append(g)

    sq_model = sq_base = 0.0
    n = 0
    bucket_n = [0] * CALIBRATION_BUCKETS
    bucket_p = [0.0] * CALIBRATION_BUCKETS
    bucket_y = [0] * CALIBRATION_BUCKETS

    for season in range(first, last + 1):
        for week in range(1, 19):
            targets = by_week.get((season, week))
            if not targets:
                continue
            ctx = context_cls(games, season, week, stat=stat)
            for g in targets:
                if len(ctx.history.get(g.player_id, [])) < BACKTEST_MIN_HISTORY:
                    continue
                m_vals, m_wts = ctx.predict(g.player_id, g.opponent)
                b_vals, b_wts = ctx.raw_samples(g.player_id)
                if spec.kind == "count":
                    b_vals = np.array([b_vals.mean()]) if len(b_vals) else b_vals
                    b_wts = np.ones(len(b_vals))
                actual = spec.value(g)
                for t in spec.thresholds:
                    outcome = 1.0 if actual >= t else 0.0
                    p_model = prob_for_stat(spec, m_vals, m_wts, t)
                    p_base = prob_for_stat(spec, b_vals, b_wts, t)
                    sq_model += (p_model - outcome) ** 2
                    sq_base += (p_base - outcome) ** 2
                    n += 1
                    b = min(int(p_model * CALIBRATION_BUCKETS), CALIBRATION_BUCKETS - 1)
                    bucket_n[b] += 1
                    bucket_p[b] += p_model
                    bucket_y[b] += int(outcome)

    buckets = [
        {
            "predicted": round(bucket_p[i] / bucket_n[i], 3),
            "actual": round(bucket_y[i] / bucket_n[i], 3),
            "n": bucket_n[i],
        }
        for i in range(CALIBRATION_BUCKETS)
        if bucket_n[i] > 0
    ]
    return {
        "stat": stat,
        "first_season": first,
        "last_season": last,
        "predictions": n,
        "brier_model": round(sq_model / n, 4) if n else None,
        "brier_baseline": round(sq_base / n, 4) if n else None,
        "buckets": buckets,
    }
