from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from app.betting.engine import StatSpec


@dataclass(frozen=True)
class RusherGame:
    season: int
    week: int
    player_id: str
    team: str
    opponent: str
    attempts: float
    yards: float
    tds: float


RUSHER_STATS: dict[str, StatSpec] = {
    "rush_attempts": StatSpec(
        key="rush_attempts",
        value=lambda g: g.attempts,
        kind="continuous",
        thresholds=(10, 15, 20, 25),
        min_bandwidth=3.0,
        level_correction=0.95,
        line_max=40,
    ),
    "rush_yards": StatSpec(
        key="rush_yards",
        value=lambda g: g.yards,
        kind="continuous",
        thresholds=(50, 75, 100, 125),
        min_bandwidth=20.0,
        level_correction=0.95,
        line_max=200,
    ),
    "rush_tds": StatSpec(
        key="rush_tds",
        value=lambda g: g.tds,
        kind="count",
        thresholds=(1, 2),
        min_bandwidth=0.0,
        level_correction=1.0,
        line_max=3,
    ),
}


def load_rusher_games(data_dir: Path, seasons: range) -> list[RusherGame]:
    rows: dict[tuple[int, int, str], RusherGame] = {}
    for season in seasons:
        path = data_dir / f"player_stats_{season}.csv"
        if not path.exists():
            continue
        with path.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["season_type"] != "REG" or r["position"] != "RB":
                    continue
                attempts = float(r["carries"] or 0)
                if attempts <= 0:
                    continue
                game = RusherGame(
                    season=int(r["season"]),
                    week=int(r["week"]),
                    player_id=r["player_id"],
                    team=r["team"],
                    opponent=r["opponent_team"],
                    attempts=attempts,
                    yards=float(r["rushing_yards"] or 0),
                    tds=float(r["rushing_tds"] or 0),
                )
                rows[(game.season, game.week, game.player_id)] = game
    return list(rows.values())
