"""Backfill minimal player_dim rows for players who have game stats but no
roster entry -- typically brand-new players (rookies especially) not yet in
players_NFL.csv. Sourced from the player_stats weekly CSVs, which carry a
display name, position, and headshot for every player regardless of how
stale the roster file is.

Only inserts; never touches an existing player_dim row.

Usage:
    python scripts/backfill_player_dim.py --season 2026
"""
from __future__ import annotations

import argparse
import asyncio
import csv
from pathlib import Path

from sqlalchemy import select

from app.db import get_sessionmaker
from app.models import PlayerDim


def _latest_rows(csv_dir: Path, season: int) -> dict[str, dict]:
    """Most recent (by week) row per gsis_id across every CSV for this season."""
    best: dict[str, tuple[int, dict]] = {}
    for path in sorted(csv_dir.glob(f"player_stats_{season}*.csv")):
        with path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                gsis_id = row.get("player_id")
                if not gsis_id or int(row["season"]) != season:
                    continue
                week = int(row["week"])
                if gsis_id not in best or week >= best[gsis_id][0]:
                    best[gsis_id] = (week, row)
    return {gsis_id: row for gsis_id, (week, row) in best.items()}


async def backfill(csv_dir: Path, season: int) -> None:
    latest = _latest_rows(csv_dir, season)
    sm = get_sessionmaker()
    async with sm() as session:
        existing = set((await session.execute(select(PlayerDim.gsis_id))).scalars().all())
        missing = {gid: row for gid, row in latest.items() if gid not in existing}
        print(f"{len(missing)} players have {season} game stats but no player_dim row.")
        for gsis_id, row in missing.items():
            session.add(
                PlayerDim(
                    gsis_id=gsis_id,
                    display_name=row.get("player_display_name") or row.get("player_name") or None,
                    position=row.get("position") or None,
                    position_group=row.get("position_group") or None,
                    headshot=row.get("headshot_url") or None,
                    latest_team=row.get("team") or None,
                )
            )
        await session.commit()
        print(f"Inserted {len(missing)} player_dim rows.")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--csv-dir", type=Path, default=Path("data/player_stats"))
    p.add_argument("--season", type=int, required=True)
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(backfill(args.csv_dir, args.season))
