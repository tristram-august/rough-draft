"""
Ingest the nflverse schedule feed (games.csv) into the `game` table.

    python scripts/ingest_schedules.py                      # all seasons, from the web
    python scripts/ingest_schedules.py --from-year 2024     # recent only
    python scripts/ingest_schedules.py --csv ./games.csv    # from a local file

game_id matches player_game_stat.game_id, so schedules join straight onto
existing stats. Team codes are normalized to match the `team` table.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import io
import urllib.request
from datetime import date
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert

from app.db import get_sessionmaker
from app.models import Game

SOURCE_URL = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"

# nflverse uses LA for the Rams; this repo's `team` table uses LAR. The rest are
# franchises that relocated, mapped onto their current code.
TEAM_ALIASES = {
    "LA": "LAR",
    "STL": "LAR",
    "OAK": "LV",
    "SD": "LAC",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ingest nflverse games.csv into the game table.")
    p.add_argument("--csv", type=Path, default=None, help="Local games.csv (defaults to fetching from nflverse).")
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


def _bool(val: str) -> bool | None:
    if val in ("", None):
        return None
    return val.strip() in ("1", "1.0", "True", "true", "TRUE")


def _date(val: str) -> date | None:
    val = (val or "").strip()
    if not val:
        return None
    try:
        return date.fromisoformat(val)
    except ValueError:
        return None


def _str(val: str, limit: int) -> str | None:
    val = (val or "").strip()
    return val[:limit] if val else None


def load_rows(csv_path: Path | None) -> list[dict]:
    if csv_path:
        raw = csv_path.read_text(encoding="utf-8")
    else:
        print(f"Fetching {SOURCE_URL}")
        req = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "rough-draft-ingest"})
        raw = urllib.request.urlopen(req, timeout=60).read().decode("utf-8")
    return list(csv.DictReader(io.StringIO(raw)))


async def ingest(csv_path: Path | None, from_year: int, to_year: int) -> None:
    rows = load_rows(csv_path)
    print(f"CSV: {len(rows)} total rows")

    payload: list[dict] = []
    skipped = 0
    for r in rows:
        season = _int(r.get("season", ""))
        game_id = (r.get("game_id") or "").strip()
        if season is None or not game_id or not (from_year <= season <= to_year):
            skipped += 1
            continue

        payload.append(
            {
                "game_id": game_id[:32],
                "season": season,
                "game_type": _str(r.get("game_type", ""), 8),
                "week": _int(r.get("week", "")),
                "gameday": _date(r.get("gameday", "")),
                "weekday": _str(r.get("weekday", ""), 12),
                "gametime": _str(r.get("gametime", ""), 8),
                "away_team": _team(r.get("away_team", "")),
                "home_team": _team(r.get("home_team", "")),
                "away_score": _int(r.get("away_score", "")),
                "home_score": _int(r.get("home_score", "")),
                "result": _float(r.get("result", "")),
                "overtime": _bool(r.get("overtime", "")),
                "spread_line": _float(r.get("spread_line", "")),
                "total_line": _float(r.get("total_line", "")),
                "div_game": _bool(r.get("div_game", "")),
                "roof": _str(r.get("roof", ""), 16),
                "surface": _str(r.get("surface", ""), 24),
                "stadium": _str(r.get("stadium", ""), 64),
                "location": _str(r.get("location", ""), 16),
                "away_qb_name": _str(r.get("away_qb_name", ""), 64),
                "home_qb_name": _str(r.get("home_qb_name", ""), 64),
                "away_coach": _str(r.get("away_coach", ""), 64),
                "home_coach": _str(r.get("home_coach", ""), 64),
            }
        )

    print(f"In range {from_year}-{to_year}: {len(payload)} games ({skipped} out of range)")

    sm = get_sessionmaker()
    upserted = 0
    async with sm() as session:
        for i in range(0, len(payload), 500):
            chunk = payload[i : i + 500]
            stmt = insert(Game).values(chunk)
            # Re-running updates scores as games finish.
            stmt = stmt.on_conflict_do_update(
                index_elements=[Game.game_id],
                set_={c.name: stmt.excluded[c.name] for c in Game.__table__.columns if c.name != "game_id"},
            )
            await session.execute(stmt)
            upserted += len(chunk)
            print(f"  upserted {upserted}/{len(payload)}")
        await session.commit()

    print(f"Done — {upserted} games upserted.")


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(ingest(args.csv, args.from_year, args.to_year))
