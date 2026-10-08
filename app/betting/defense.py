from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

PRIOR_SEASON_WEIGHT = 0.5
SHRINK_GAMES = 10.0
MIN_GAMES_FOR_SEASON_MEAN = 20


@dataclass(frozen=True)
class TeamDefenseGame:
    season: int
    week: int
    team: str
    sacks: float
    ints: float


def load_team_defense(data_dir: Path, seasons: range) -> list[TeamDefenseGame]:
    totals: dict[tuple[int, int, str], list[float]] = defaultdict(lambda: [0.0, 0.0])
    for season in seasons:
        path = data_dir / f"player_stats_{season}.csv"
        if not path.exists():
            continue
        with path.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["season_type"] != "REG":
                    continue
                key = (int(r["season"]), int(r["week"]), r["team"])
                totals[key][0] += float(r["def_sacks"] or 0)
                totals[key][1] += float(r["def_interceptions"] or 0)
    return [
        TeamDefenseGame(season=s, week=w, team=t, sacks=v[0], ints=v[1]) for (s, w, t), v in totals.items()
    ]


class TeamDefenseFactors:
    """As-of shrunk factors (relative to league average) for a team's sacks and
    interceptions forced, built the same way as the receiver/passer defense
    adjustments elsewhere: current-season weight 1.0, prior season 0.5, shrunk
    toward 1.0 by sample size."""

    def __init__(self, games: list[TeamDefenseGame], season: int, week: int) -> None:
        history = [g for g in games if (g.season, g.week) < (season, week)]

        def league_means(stat: str) -> dict[int, float]:
            by_season: dict[int, list[float]] = defaultdict(list)
            for g in games:
                if g.season < season:
                    by_season[g.season].append(getattr(g, stat))
            means = {s: sum(v) / len(v) for s, v in by_season.items()}
            current = [getattr(g, stat) for g in history if g.season == season]
            if len(current) >= MIN_GAMES_FOR_SEASON_MEAN or season - 1 not in means:
                if current:
                    means[season] = sum(current) / len(current)
                elif history:
                    means[season] = sum(getattr(g, stat) for g in history) / len(history)
                else:
                    means[season] = 1.0
            else:
                means[season] = means[season - 1]
            return means

        self.factors: dict[str, dict[str, float]] = defaultdict(dict)
        for stat in ("sacks", "ints"):
            means = league_means(stat)
            sums: dict[str, float] = defaultdict(float)
            weights: dict[str, float] = defaultdict(float)
            for g in history:
                if g.season == season:
                    w = 1.0
                elif g.season == season - 1:
                    w = PRIOR_SEASON_WEIGHT
                else:
                    continue
                m = means.get(g.season)
                if not m:
                    continue
                sums[g.team] += w * getattr(g, stat) / m
                weights[g.team] += w
            for team, w in weights.items():
                observed = sums[team] / w
                self.factors[team][stat] = (w * observed + SHRINK_GAMES) / (w + SHRINK_GAMES)

    def factor(self, team: str, stat: str) -> float:
        return self.factors.get(team, {}).get(stat, 1.0)
