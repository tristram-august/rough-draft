# scripts/ingest_player_stats_subset.py
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]  # /app
sys.path.insert(0, str(REPO_ROOT))

import argparse
import asyncio
import csv
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


def _norm(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    if s == "" or s.lower() == "nan":
        return None
    return s


def _to_int(v: Any) -> int | None:
    s = _norm(v)
    if s is None:
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def _to_float(v: Any) -> float | None:
    s = _norm(v)
    if s is None:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _year_from_name(path: Path) -> int | None:
    digits = "".join(ch for ch in path.stem if ch.isdigit())
    if len(digits) >= 4:
        return int(digits[:4])
    return None


# Preferred keys first; aliases later. We use setdefault so first parsed value wins.
COLMAP: dict[str, str] = {
    # identity
    "player_id": "player_gsis_id",
    "season": "season",
    "week": "week",
    "season_type": "season_type",
    "game_id": "game_id",  # may be missing; we synthesize
    "team": "team",
    "opponent_team": "opponent_team",
    "position_group": "position_group",

    # passing
    "completions": "pass_completions",
    "attempts": "pass_attempts",
    "passing_yards": "pass_yards",
    "passing_tds": "pass_tds",
    "interceptions": "pass_ints",
    "passing_interceptions": "pass_ints",
    "passing_epa": "passing_epa",
    "passing_cpoe": "passing_cpoe",

    # rushing
    "carries": "rush_attempts",
    "rushing_yards": "rush_yards",
    "rushing_tds": "rush_tds",
    "rushing_epa": "rushing_epa",

    # receiving
    "targets": "targets",
    "receptions": "receptions",
    "receiving_yards": "rec_yards",
    "receiving_tds": "rec_tds",
    "receiving_epa": "receiving_epa",
    "target_share": "target_share",
    "receiving_air_yards": "air_yards",
    "air_yards_share": "air_yards_share",

    # defense (canonical)
    "def_sacks": "def_sacks",
    "def_interceptions": "def_ints",
    "interceptions_def": "def_ints",
    "def_fumbles_forced": "def_forced_fumbles",
    "forced_fumbles": "def_forced_fumbles",
    "fumble_recoveries": "def_fumble_recoveries",
    "def_tds": "def_tds",
    "tackles": "def_tackles",
    "def_tackles_solo": "def_tackles",

    # defense aliases (only fill if canonical missing)
    "sacks": "def_sacks",
    "sk": "def_sacks",
    "sack": "def_sacks",
    "def_sk": "def_sacks",
    "ints": "def_ints",
    "int": "def_ints",
    "def_int": "def_ints",
    "defensive_interceptions": "def_ints",
    "fr": "def_fumble_recoveries",
    "def_fr": "def_fumble_recoveries",
    "def_fumbles": "def_fumble_recoveries",
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
    "def_tackles",
    "def_ints",
    "def_forced_fumbles",
    "def_fumble_recoveries",
    "def_tds",
    "fumbles_lost",
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

REQUIRED_INT_DEFAULTS = {
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
    "def_tackles",
    "def_ints",
    "def_forced_fumbles",
    "def_fumble_recoveries",
    "def_tds",
    "fumbles_lost",
}

REQUIRED_FLOAT_DEFAULTS = {
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

            if not team or season is None:
                continue

            game_id = _norm(raw.get("game_id"))
            if not game_id:
                game_id = f"{season}_{season_type or 'UNK'}_{week or 0}_{team}_{opp or 'UNK'}_{player_id}"

            row: dict[str, Any] = {}

            # Map fields without clobbering earlier, more-canonical values
            for csv_col, db_col in COLMAP.items():
                if csv_col not in raw:
                    continue
                val = raw.get(csv_col)
                if val is None:
                    continue
                if isinstance(val, str) and val.strip() == "":
                    continue

                if db_col in INT_FIELDS:
                    parsed = _to_int(val)
                    if parsed is None:
                        continue
                    row.setdefault(db_col, int(parsed))
                elif db_col in FLOAT_FIELDS:
                    parsed_f = _to_float(val)
                    if parsed_f is None:
                        continue
                    row.setdefault(db_col, float(parsed_f))
                else:
                    parsed_s = _norm(val)
                    if parsed_s is None:
                        continue
                    row.setdefault(db_col, str(parsed_s))

            # fumbles_lost: sum across common lost columns (avoids last-one-wins)
            fum_lost = 0
            fum_lost += _to_int(raw.get("fumbles_lost")) or 0
            fum_lost += _to_int(raw.get("receiving_fumbles_lost")) or 0
            fum_lost += _to_int(raw.get("rushing_fumbles_lost")) or 0
            fum_lost += _to_int(raw.get("sack_fumbles_lost")) or 0
            row["fumbles_lost"] = fum_lost

            # Required keys
            row["player_gsis_id"] = player_id
            row["game_id"] = game_id
            row["team"] = team
            row["season"] = season

            # Defaults (don't overwrite real values)
            row.setdefault("def_sacks", 0.0)
            row.setdefault("def_ints", 0)
            row.setdefault("def_forced_fumbles", 0)
            row.setdefault("def_fumble_recoveries", 0)
            row.setdefault("def_tds", 0)
            row.setdefault("def_tackles", 0)
            row.setdefault("pass_ints", 0)
            
            # Ensure consistent columns across multi-row insert (prevents SQLAlchemy boundparameter CompileError)
            for k in REQUIRED_INT_DEFAULTS:
                row.setdefault(k, 0)

            for k in REQUIRED_FLOAT_DEFAULTS:
                row.setdefault(k, 0.0)

            # sanity check: no SQLAlchemy objects in row
            bad = [k for k, v in row.items() if type(v).__module__.startswith("sqlalchemy")]
            if bad:
                raise RuntimeError(f"Non-python values in row: {bad} -> {[type(row[k]) for k in bad]}")

            batch.append(row)
            if len(batch) >= 250:
                inserted += await _flush_batch(session, batch)
                batch.clear()

    if batch:
        inserted += await _flush_batch(session, batch)

    return inserted


async def _flush_batch(session: AsyncSession, rows: list[dict[str, Any]]) -> int:
    table = PlayerGameStat.__table__

    stmt = insert(table).values(rows)

    update_cols = {
        c.name: getattr(stmt.excluded, c.name)
        for c in table.columns
        if c.name != "id"
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