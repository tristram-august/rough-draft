from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np

from app.betting.engine import (
    DEFENSE_SHRINK_GAMES,
    HALF_LIFE_GAMES,
    MIN_GAMES_FOR_SEASON_SCALE,
    PRIOR_SEASON_WEIGHT,
    StatSpec,
)

COUNT_PRIOR_GAMES = 8.0
COUNT_OPPONENT_ADJUST = False


@dataclass(frozen=True)
class PasserGame:
    season: int
    week: int
    player_id: str
    team: str
    opponent: str
    attempts: float
    pass_yards: float
    pass_tds: float
    ints: float


PASSER_STATS: dict[str, StatSpec] = {
    "pass_attempts": StatSpec(
        key="pass_attempts",
        value=lambda g: g.attempts,
        kind="continuous",
        thresholds=(25, 30, 35, 40, 45),
        min_bandwidth=4.0,
        level_correction=1.0,
        line_max=60,
    ),
    "pass_yards": StatSpec(
        key="pass_yards",
        value=lambda g: g.pass_yards,
        kind="continuous",
        thresholds=(150, 200, 250, 300),
        min_bandwidth=25.0,
        level_correction=1.0,
        line_max=450,
    ),
    "pass_tds": StatSpec(
        key="pass_tds",
        value=lambda g: g.pass_tds,
        kind="count",
        thresholds=(1, 2, 3),
        min_bandwidth=0.0,
        level_correction=1.0,
        line_max=5,
    ),
    "interceptions": StatSpec(
        key="interceptions",
        value=lambda g: g.ints,
        kind="count",
        thresholds=(1, 2),
        min_bandwidth=0.0,
        level_correction=1.0,
        line_max=4,
    ),
}


def load_passer_games(data_dir: Path, seasons: range) -> list[PasserGame]:
    rows: dict[tuple[int, int, str], PasserGame] = {}
    for season in seasons:
        path = data_dir / f"player_stats_{season}.csv"
        if not path.exists():
            continue
        with path.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["season_type"] != "REG" or r["position"] != "QB":
                    continue
                attempts = float(r["attempts"] or 0)
                if attempts <= 0:
                    continue
                game = PasserGame(
                    season=int(r["season"]),
                    week=int(r["week"]),
                    player_id=r["player_id"],
                    team=r["team"],
                    opponent=r["opponent_team"],
                    attempts=attempts,
                    pass_yards=float(r["passing_yards"] or 0),
                    pass_tds=float(r["passing_tds"] or 0),
                    ints=float(r["passing_interceptions"] or 0),
                )
                rows[(game.season, game.week, game.player_id)] = game
    return list(rows.values())


class GameLevelContext:
    """Everything knowable before (season, week) kicks off, and nothing after."""

    def __init__(
        self,
        games: list,
        season: int,
        week: int,
        stat: str = "pass_yards",
        specs: dict[str, StatSpec] | None = None,
    ) -> None:
        self.season = season
        self.stat = stat
        self.spec = (specs or PASSER_STATS)[stat]
        history = [g for g in games if (g.season, g.week) < (season, week)]

        by_season: dict[int, list[float]] = defaultdict(list)
        for g in games:
            if g.season < season:
                by_season[g.season].append(self.spec.value(g))
        self.means: dict[int, float] = {s: sum(v) / len(v) for s, v in by_season.items()}

        current = [self.spec.value(g) for g in history if g.season == season]
        if len(current) >= MIN_GAMES_FOR_SEASON_SCALE or season - 1 not in self.means:
            base = current or [self.spec.value(g) for g in history]
            self.means[season] = sum(base) / len(base)
        else:
            self.means[season] = self.means[season - 1]

        allowed_sum: dict[str, float] = defaultdict(float)
        allowed_weight: dict[str, float] = defaultdict(float)
        for g in history:
            if g.season == season:
                weight = 1.0
            elif g.season == season - 1:
                weight = PRIOR_SEASON_WEIGHT
            else:
                continue
            allowed_sum[g.opponent] += weight * self.spec.value(g) / self.means[g.season]
            allowed_weight[g.opponent] += weight

        self.defense: dict[str, float] = {}
        for team, weight in allowed_weight.items():
            observed = allowed_sum[team] / weight
            self.defense[team] = (weight * observed + DEFENSE_SHRINK_GAMES) / (weight + DEFENSE_SHRINK_GAMES)

        self.history: dict[str, list[PasserGame]] = defaultdict(list)
        for g in sorted(history, key=lambda g: (g.season, g.week)):
            self.history[g.player_id].append(g)

    def predict(self, player_id: str, next_opponent: str) -> tuple[np.ndarray, np.ndarray]:
        hist = self.history.get(player_id, [])
        cur = self.means[self.season]
        if self.spec.kind == "count":
            prior = cur
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

        n = len(hist)
        recency = 0.5 ** (np.arange(n)[::-1] / HALF_LIFE_GAMES)
        opp_factor = self.defense.get(next_opponent, 1.0)
        values = np.array(
            [
                self.spec.value(g) / self.means[g.season] / self.defense.get(g.opponent, 1.0) * opp_factor * cur
                for g in hist
            ]
        )
        return self.spec.level_correction * values, recency

    def raw_samples(self, player_id: str) -> tuple[np.ndarray, np.ndarray]:
        hist = self.history.get(player_id, [])
        return np.array([self.spec.value(g) for g in hist]), np.ones(len(hist))
