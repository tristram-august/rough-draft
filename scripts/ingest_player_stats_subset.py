from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]  # /app
sys.path.insert(0, str(REPO_ROOT))

import argparse
import asyncio
import csv
from pathlib import Path
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_sessionmaker
from app.models import PlayerGameStat


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ingest player_stats_YYYY.csv files into player_game_stat (drawer subset).")
    p.add_argument("--csv-dir", required=True, help="Folder containing yearly player_stats CSVs (e.g. ./data/player_stats)")
    p.add_argument("--from-year", type=int, default=2000)
    p.add_argument("--to-year", type=int, default=2100)
    return p.parse_args()


def _norm(v: str | None) -> str | None:
    if v is None:
        return None
    s = v.strip()
    return None if s == "" or s.lower() == "nan" else s


def _to_int(v: str | None) -> int | None:
    s = _norm(v)
    if s is None:
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def _to_float(v: str | None) -> float | None:
    s = _norm(v)
    if s is None:
        return None
    try:
        return float(s)
    except ValueError:
        return None
    
def _year_from_name(path: Path) -> int | None:
    # Accept: 2025.csv, player_stats_2025.csv, etc.
    digits = "".join(ch for ch in path.stem if ch.isdigit())
    if len(digits) >= 4:
        return int(digits[:4])
    return None


# Map your CSV columns -> DB columns.
# If a CSV column name differs, update here (don’t touch DB schema yet).
COLMAP: dict[str, str] = {
    # identity
    "player_id": "player_gsis_id",
    "season": "season",
    "week": "week",
    "season_type": "season_type",
    "game_id": "game_id",  # may be missing in older CSVs; we'll synthesize in ingest_file()
    "team": "team",
    "opponent_team": "opponent_team",
    "position_group": "position_group",

    # passing
    "completions": "pass_completions",
    "attempts": "pass_attempts",
    "passing_yards": "pass_yards",
    "passing_tds": "pass_tds",
    # 2025-style vs 2000-style naming
    "interceptions": "pass_ints",
    "passing_interceptions": "pass_ints",
    "passing_epa": "passing_epa",
    "passing_cpoe": "passing_cpoe",

    # rushing
    "carries": "rush_attempts",
    "rushing_yards": "rush_yards",
    "rushing_tds": "rush_tds",
    "rushing_epa": "rushing_epa",

    # receiving (volume-first)
    "targets": "targets",
    "receptions": "receptions",
    "receiving_yards": "rec_yards",
    "receiving_tds": "rec_tds",
    "receiving_epa": "receiving_epa",
    "target_share": "target_share",
    "receiving_air_yards": "air_yards",
    "air_yards_share": "air_yards_share",

    # ball security (different datasets expose different "lost" columns)
    "fumbles_lost": "fumbles_lost",
    "receiving_fumbles_lost": "fumbles_lost",
    "rushing_fumbles_lost": "fumbles_lost",
    "sack_fumbles_lost": "fumbles_lost",

    # defense
    "tackles": "def_tackles",
    "def_tackles_solo": "def_tackles",
    "def_sacks": "def_sacks",
    "sacks": "def_sacks",
    "def_interceptions": "def_ints",
    "interceptions_def": "def_ints",
    "forced_fumbles": "def_forced_fumbles",
    "def_fumbles_forced": "def_forced_fumbles",
    "fumble_recoveries": "def_fumble_recoveries",
    "def_tds": "def_tds",
}


INT_FIELDS = {
    "season",
    "week",
    "pass_completions",
    "pass_attempts",
    "pass_yards",
    "pass_tds",
    "pass_ints",
    "rush_attempts",
    "rush_yards",
    "rush_tds",
    "targets",
    "receptions",
    "rec_yards",
    "rec_tds",
    "air_yards",
    "fumbles_lost",
    "def_tackles",
    "def_ints",
    "def_forced_fumbles",
    "def_fumble_recoveries",
    "def_tds",
}

FLOAT_FIELDS = {
    "passing_epa",
    "passing_cpoe",
    "rushing_epa",
    "receiving_epa",
    "target_share",
    "air_yards_share",
    "def_sacks",
}


async def ingest_file(session: AsyncSession, path: Path) -> int:
    inserted = 0
    batch: list[dict[str, Any]] = []

    with path.open("r", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for raw in r:
            player_id = _norm(raw.get("player_id"))

            # Skip bogus/non-player rows in early years
            if not player_id or not player_id.startswith("00-"):
                continue

            team = _norm(raw.get("team"))
            opp = _norm(raw.get("opponent_team"))
            season = _to_int(raw.get("season"))
            week = _to_int(raw.get("week"))
            season_type = _norm(raw.get("season_type"))

            game_id = _norm(raw.get("game_id"))

            if not team or season is None:
                continue

            if not game_id:
                game_id = f"{season}_{season_type or 'UNK'}_{week or 0}_{team}_{opp or 'UNK'}_{player_id}"

            row: dict[str, Any] = {}
            for csv_col, db_col in COLMAP.items():
                val = raw.get(csv_col)
                if db_col in INT_FIELDS:
                    row[db_col] = _to_int(val)
                elif db_col in FLOAT_FIELDS:
                    row[db_col] = _to_float(val)
                else:
                    row[db_col] = _norm(val)

            row["player_gsis_id"] = player_id
            row["game_id"] = game_id
            row["team"] = team
            row["season"] = season

            batch.append(row)
            if len(batch) >= 250:


                inserted += await _flush_batch(session, batch)
                batch.clear()

    if batch:
        inserted += await _flush_batch(session, batch)

    return inserted


async def _flush_batch(session: AsyncSession, rows: list[dict[str, Any]]) -> int:
    stmt = insert(PlayerGameStat).values(rows)
    update_cols = {
        c.name: getattr(stmt.excluded, c.name)
        for c in PlayerGameStat.__table__.columns
        if c.name not in ("id",)
    }
    stmt = stmt.on_conflict_do_update(
        constraint="uq_player_game_team",
        set_=update_cols,
    )
    await session.execute(stmt)
    return len(rows)


async def main() -> None:
    args = parse_args()
    csv_dir = Path(args.csv_dir).expanduser().resolve()
    if not csv_dir.exists():
        raise SystemExit(f"csv dir not found: {csv_dir}")

    files = sorted(p for p in csv_dir.glob("*.csv") if p.is_file())
    filtered: list[Path] = []
    for p in files:
        y = _year_from_name(p)
        if y is None:
            continue
        if args.from_year <= y <= args.to_year:
            filtered.append(p)

    if not filtered:
        raise SystemExit("No CSV files matched year range")

    session_maker = get_sessionmaker()
    async with session_maker() as session:  # type: AsyncSession
        total = 0
        for p in filtered:
            n = await ingest_file(session, p)
            total += n
            print(f"{p.name}: {n}")
        await session.commit()

    print(f"Done. Upserted {total} rows from {len(filtered)} files")


if __name__ == "__main__":
    asyncio.run(main())