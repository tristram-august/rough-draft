"""Ingest PFF OL blocking stats CSVs into ol_season_stat.

Usage:
    python scripts/ingest_ol_stats.py data/ol_stats/offense_blocking_2025.csv --season 2025
    python scripts/ingest_ol_stats.py data/ol_stats/offense_blocking_2024.csv --season 2024
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import argparse
import asyncio
import csv

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_sessionmaker
from app.models import OLSeasonStat, Player

OL_POSITIONS = {"T", "G", "C"}


def _int(val: str) -> int | None:
    try:
        return int(float(val)) if val else None
    except (ValueError, TypeError):
        return None


def _float(val: str) -> float | None:
    try:
        return float(val) if val else None
    except (ValueError, TypeError):
        return None


async def ingest(csv_path: Path, season: int) -> None:
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["position"] in OL_POSITIONS]

    print(f"CSV: {len(rows)} OL rows for season {season}")

    sm = get_sessionmaker()
    async with sm() as session:
        # Build name → player_id lookup
        res = await session.execute(select(Player.id, Player.full_name))
        name_to_id: dict[str, int] = {name: pid for pid, name in res.all()}

        inserted = skipped = 0
        for row in rows:
            player_id = name_to_id.get(row["player"])
            if player_id is None:
                skipped += 1
                continue

            stmt = (
                insert(OLSeasonStat)
                .values(
                    player_id=player_id,
                    pff_player_id=_int(row["player_id"]),
                    season=season,
                    position=row["position"] or None,
                    team_abbrev=row["team_name"] or None,
                    games=_int(row["player_game_count"]),
                    snap_counts_offense=_int(row["snap_counts_offense"]),
                    pressures_allowed=_int(row["pressures_allowed"]),
                    hurries_allowed=_int(row["hurries_allowed"]),
                    hits_allowed=_int(row["hits_allowed"]),
                    sacks_allowed=_int(row["sacks_allowed"]),
                    pbe=_float(row["pbe"]),
                    pass_block_percent=_float(row["pass_block_percent"]),
                    penalties=_int(row["penalties"]),
                )
                .on_conflict_do_update(
                    constraint="uq_ol_player_season",
                    set_={
                        "pff_player_id": _int(row["player_id"]),
                        "position": row["position"] or None,
                        "team_abbrev": row["team_name"] or None,
                        "games": _int(row["player_game_count"]),
                        "snap_counts_offense": _int(row["snap_counts_offense"]),
                        "pressures_allowed": _int(row["pressures_allowed"]),
                        "hurries_allowed": _int(row["hurries_allowed"]),
                        "hits_allowed": _int(row["hits_allowed"]),
                        "sacks_allowed": _int(row["sacks_allowed"]),
                        "pbe": _float(row["pbe"]),
                        "pass_block_percent": _float(row["pass_block_percent"]),
                        "penalties": _int(row["penalties"]),
                    },
                )
            )
            await session.execute(stmt)
            inserted += 1

        await session.commit()

    print(f"Done — inserted/updated: {inserted}, skipped (no player match): {skipped}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path, help="Path to PFF blocking CSV")
    parser.add_argument("--season", type=int, required=True, help="Season year (e.g. 2025)")
    args = parser.parse_args()
    asyncio.run(ingest(args.csv, args.season))
