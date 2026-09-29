"""
Ingest nflverse's team-game box scores into `team_game_stat` -- a subset of
stats_team_week_YYYY.csv, same "drawer" philosophy as
ingest_player_stats_subset.py (drops per-kick/punt trivia like fg_made_list
that nothing here needs).

    python scripts/ingest_team_stats.py                        # 1999-present, fetched from nflverse
    python scripts/ingest_team_stats.py --from-year 2010 --to-year 2024
    python scripts/ingest_team_stats.py --csv-dir ./data/team_stats  # local files instead

Unlike games.csv (one combined file for all seasons), nflverse publishes team
stats one file per season: stats_team_week_YYYY.csv, at a stable public URL
(https://github.com/nflverse/nflverse-data/releases/tag/stats_team) --
confirmed by fetching stats_team_week_2026.csv directly and diffing its
header/row count against a CSV pulled the same day via nflreadpy.

Team codes are normalized the same way as ingest_schedules.py (LA -> LAR
etc.) so this joins cleanly onto game.team / player_game_stat.team.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import io
import urllib.request
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert

from app.db import get_sessionmaker
from app.models import TeamGameStat
from scripts.ingest_schedules import TEAM_ALIASES

SOURCE_URL_TEMPLATE = "https://github.com/nflverse/nflverse-data/releases/download/stats_team/stats_team_week_{season}.csv"

INT_COLS = [
    "completions", "attempts", "passing_yards", "passing_tds", "passing_interceptions",
    "carries", "rushing_yards", "rushing_tds",
    "receptions", "targets", "receiving_yards", "receiving_tds",
    "sack_fumbles_lost", "rushing_fumbles_lost", "receiving_fumbles_lost",
    "def_tackles_for_loss", "def_fumbles_forced", "def_qb_hits", "def_interceptions", "def_tds",
    "fg_made", "fg_att", "pat_made", "pat_att", "penalties", "penalty_yards",
]
FLOAT_COLS = ["passing_epa", "passing_cpoe", "rushing_epa", "receiving_epa", "def_sacks"]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ingest nflverse team-game box scores into team_game_stat.")
    p.add_argument("--csv-dir", type=Path, default=None, help="Local stats_team_week_YYYY.csv files instead of fetching.")
    p.add_argument("--from-year", type=int, default=1999)
    p.add_argument("--to-year", type=int, default=2100)
    return p.parse_args()


def _team(val: str) -> str:
    val = (val or "").strip().upper()
    return TEAM_ALIASES.get(val, val)


def _int(val: str) -> int | None:
    try:
        return int(float(val)) if val not in ("", None) else None
    except (ValueError, TypeError):
        return None


def _float(val: str) -> float | None:
    try:
        return float(val) if val not in ("", None) else None
    except (ValueError, TypeError):
        return None


def _str(val: str, limit: int) -> str | None:
    val = (val or "").strip()
    return val[:limit] if val else None


def load_season_rows(season: int, csv_dir: Path | None) -> list[dict]:
    if csv_dir:
        path = csv_dir / f"stats_team_week_{season}.csv"
        if not path.exists():
            return []
        raw = path.read_text(encoding="utf-8")
    else:
        url = SOURCE_URL_TEMPLATE.format(season=season)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "rough-draft-ingest"})
            raw = urllib.request.urlopen(req, timeout=60).read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return []
            raise
    return list(csv.DictReader(io.StringIO(raw)))


async def ingest(csv_dir: Path | None, from_year: int, to_year: int) -> None:
    sm = get_sessionmaker()
    total = 0
    async with sm() as session:
        for season in range(from_year, to_year + 1):
            rows = load_season_rows(season, csv_dir)
            if not rows:
                continue

            payload = []
            for r in rows:
                game_id = (r.get("game_id") or "").strip()
                team = _team(r.get("team", ""))
                if not game_id or not team:
                    continue
                row = {
                    "season": _int(r.get("season", "")) or season,
                    "week": _int(r.get("week", "")),
                    "season_type": _str(r.get("season_type", ""), 8),
                    "game_id": game_id[:32],
                    "team": team,
                    "opponent_team": _team(r.get("opponent_team", "")) or None,
                }
                for c in INT_COLS:
                    row[c] = _int(r.get(c, ""))
                for c in FLOAT_COLS:
                    row[c] = _float(r.get(c, ""))
                payload.append(row)

            if not payload:
                continue

            for i in range(0, len(payload), 500):
                chunk = payload[i : i + 500]
                stmt = insert(TeamGameStat).values(chunk)
                stmt = stmt.on_conflict_do_update(
                    constraint="uq_team_game",
                    set_={c.name: stmt.excluded[c.name] for c in TeamGameStat.__table__.columns if c.name not in ("id", "game_id", "team")},
                )
                await session.execute(stmt)

            total += len(payload)
            print(f"{season}: {len(payload)} team-games")

        await session.commit()

    print(f"Done -- {total} team-game rows upserted.")


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(ingest(args.csv_dir, args.from_year, args.to_year))
