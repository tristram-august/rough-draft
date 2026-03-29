from __future__ import annotations

import sys
from pathlib import Path

# Force local repo "app/" package to win over any installed "app" package.
REPO_ROOT = Path(__file__).resolve().parents[1]  # /app
sys.path.insert(0, str(REPO_ROOT))

import argparse
import asyncio
import csv
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_sessionmaker
from app.models import PlayerDim


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ingest players_NFL.csv into player_dim.")
    p.add_argument("--csv", required=True, help="Path to players_NFL.csv (e.g. ./data/players/players_NFL.csv)")
    return p.parse_args()


def _to_int(v: str | None) -> int | None:
    if v is None:
        return None
    s = v.strip()
    if s == "" or s.lower() == "nan":
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def _to_date(v: str | None):
    if v is None:
        return None
    s = v.strip()
    if s == "" or s.lower() == "nan":
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _norm(v: str | None) -> str | None:
    if v is None:
        return None
    s = v.strip()
    return None if s == "" or s.lower() == "nan" else s


async def main() -> None:
    args = parse_args()
    path = Path(args.csv).expanduser().resolve()
    if not path.exists():
        raise SystemExit(f"csv not found: {path}")

    rows: list[dict[str, Any]] = []
    with path.open("r", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for d in r:
            gsis_id = _norm(d.get("gsis_id"))
            if not gsis_id:
                continue

            rows.append(
                {
                    "gsis_id": gsis_id,
                    "pfr_id": _norm(d.get("pfr_id")),
                    "espn_id": _norm(d.get("espn_id")),
                    "pff_id": _norm(d.get("pff_id")),
                    "nfl_id": _norm(d.get("nfl_id")),
                    "display_name": _norm(d.get("display_name")),
                    "first_name": _norm(d.get("first_name")),
                    "last_name": _norm(d.get("last_name")),
                    "short_name": _norm(d.get("short_name")),
                    "football_name": _norm(d.get("football_name")),
                    "suffix": _norm(d.get("suffix")),
                    "birth_date": _to_date(d.get("birth_date")),
                    "height": _to_int(d.get("height")),
                    "weight": _to_int(d.get("weight")),
                    "headshot": _norm(d.get("headshot")),
                    "position": _norm(d.get("position")),
                    "position_group": _norm(d.get("position_group")),
                    "ngs_position": _norm(d.get("ngs_position")),
                    "ngs_position_group": _norm(d.get("ngs_position_group")),
                    "latest_team": _norm(d.get("latest_team")),
                    "status": _norm(d.get("status")),
                    "ngs_status": _norm(d.get("ngs_status")),
                    "ngs_status_short_description": _norm(d.get("ngs_status_short_description")),
                    "years_of_experience": _to_int(d.get("years_of_experience")),
                    "rookie_season": _to_int(d.get("rookie_season")),
                    "last_season": _to_int(d.get("last_season")),
                    "draft_year": _to_int(d.get("draft_year")),
                    "draft_round": _to_int(d.get("draft_round")),
                    "draft_pick": _to_int(d.get("draft_pick")),
                    "draft_team": _norm(d.get("draft_team")),
                    "college_name": _norm(d.get("college_name")),
                    "college_conference": _norm(d.get("college_conference")),
                    "jersey_number": _to_int(d.get("jersey_number")),
                }
            )

    session_maker = get_sessionmaker()
    async with session_maker() as session:  # type: AsyncSession
        if rows:
            session_maker = get_sessionmaker()
            async with session_maker() as session:  # type: AsyncSession
                BATCH_SIZE = 800  # safe for postgres parameter limit

                for i in range(0, len(rows), BATCH_SIZE):
                    chunk = rows[i : i + BATCH_SIZE]
                    stmt = insert(PlayerDim).values(chunk)
                    update_cols = {
                        c.name: getattr(stmt.excluded, c.name)
                        for c in PlayerDim.__table__.columns
                        if c.name != "gsis_id"
                    }
                    stmt = stmt.on_conflict_do_update(index_elements=["gsis_id"], set_=update_cols)
                    await session.execute(stmt)
                    print(f"Upserted {min(i + BATCH_SIZE, len(rows))}/{len(rows)}")

                await session.commit()

    print(f"Ingested/updated {len(rows)} player_dim rows")


if __name__ == "__main__":
    asyncio.run(main())