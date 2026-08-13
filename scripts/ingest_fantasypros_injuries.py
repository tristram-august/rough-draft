"""
Pull the current NFL injury report from the FantasyPros public API into
`player_injury`.

    python scripts/ingest_fantasypros_injuries.py --season 2026

Requires FANTASYPROS_API_KEY on a plan without the free tier's 10-row cap
(see scripts/ingest_fantasypros.py for that whole saga).

One call: GET /nfl/injuries?year={season}&include_probabilities=true. No
`week` param needed -- confirmed live, this returns the full current report
(~100-300 rows) regardless.

Player-name linking reuses ingest_fantasy_ranks.py's NameIndex exactly like
ingest_fantasypros.py does. `--season` here is only fed into build_name_index
to disambiguate active players (see NameIndex docstring) -- player_injury
itself has no season column, since it's a live snapshot, not a per-season
table.

Unlike fantasy_rank, rows that don't resolve a gsis_id are DROPPED rather
than kept: an injury badge only ever renders next to a player already shown
elsewhere (drawer, board row), so an unlinked row has nowhere to attach.

Full delete-then-rebuild of the whole table on every run (no season/week
scope) -- same "live snapshot, rebuilt every run, no history" contract as
EloRating.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert

from app.db import get_sessionmaker
from app.fantasypros_client import fetch as _fetch, warn_if_capped as _warn_if_capped
from app.models import PlayerInjury
from scripts.ingest_fantasy_ranks import LINKABLE_POSITIONS, build_name_index


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ingest the current FantasyPros injury report into player_injury.")
    p.add_argument("--season", type=int, required=True, help="Season for name-index disambiguation (e.g. 2026)")
    return p.parse_args()


def _parse_updated_at(val: str | None) -> datetime:
    if val:
        try:
            return datetime.strptime(val, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


async def ingest(season: int) -> None:
    print("Fetching /injuries...")
    resp = _fetch("/injuries", {"year": season, "include_probabilities": "true"})
    _warn_if_capped(resp)
    injuries = resp.get("injuries") or []
    print(f"  {len(injuries)} reported")

    sm = get_sessionmaker()
    async with sm() as session:
        name_index = await build_name_index(session, season)

        payload: list[dict] = []
        linked = unlinked = 0
        for row in injuries:
            position = (row.get("position_id") or "").upper()
            name = (row.get("name") or "").strip()
            status = (row.get("status") or "").strip()
            if not name or not status or position not in LINKABLE_POSITIONS:
                unlinked += 1
                continue

            gsis_id = name_index.lookup(name, position)
            if not gsis_id:
                unlinked += 1
                continue
            linked += 1

            payload.append(
                {
                    "gsis_id": gsis_id,
                    "player_name": name[:128],
                    "team": (row.get("team_id") or "").strip()[:8] or None,
                    "position": position[:8],
                    "status": status[:32],
                    "status_short": (row.get("status_short") or "").strip()[:8] or None,
                    "injury_type": (row.get("injury_type") or "").strip()[:64] or None,
                    "comment": (row.get("comment") or "").strip() or None,
                    "probability_of_playing": (
                        str(row["probability_of_playing"])[:16] if row.get("probability_of_playing") is not None else None
                    ),
                    "updated_at": _parse_updated_at(row.get("injury_update_date")),
                }
            )

        total = linked + unlinked
        pct = (100 * linked / total) if total else 0
        print(f"Linked to player_dim: {linked}/{total} ({pct:.1f}%) — {unlinked} dropped (unlinked or not a person)")

        await session.execute(delete(PlayerInjury))
        # A player can appear more than once in the source feed under edge
        # cases (e.g. a mid-week status change); the primary key is gsis_id,
        # so re-insert the same gsis_id twice in one chunk would 500 -- keep
        # only the last occurrence per player.
        deduped = {row["gsis_id"]: row for row in payload}.values()
        deduped = list(deduped)
        for i in range(0, len(deduped), 500):
            chunk = deduped[i : i + 500]
            await session.execute(insert(PlayerInjury).values(chunk))
        await session.commit()

    print(f"Done — {len(deduped)} rows written (full rebuild).")


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(ingest(args.season))
