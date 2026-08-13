"""
Pull FantasyPros' weekly or rest-of-season fantasy-point projections into
`player_projection`.

    python scripts/ingest_fantasypros_projections.py --season 2025 --week 1
    python scripts/ingest_fantasypros_projections.py --season 2025 --ros

Requires FANTASYPROS_API_KEY on a plan without the free tier's 10-row cap.

One call per position in BOARD_POSITIONS (QB/RB/WR/TE/K/DST), 1/second:
GET /nfl/{season}/projections?position=X&week=N  (or &ros=true instead of week).

Two real discrepancies vs. the OpenAPI spec, confirmed by live calls before
writing this script -- do not "fix" these back to match the docs:
  - The player id field is `fpid`, not `player_id` like every other
    FantasyPros endpoint this app uses.
  - `stats` is a single object, not an array like the spec's schema claims.
    `points`/`points_ppr`/`points_half` live inside it, not at the top level
    of the player object. All three scoring totals come back together
    regardless of any `scoring` query param, so this script doesn't pass one.

Player-name linking reuses ingest_fantasy_ranks.py's NameIndex, same as
ingest_fantasypros.py. Unlike PlayerInjury (and like FantasyRank), unlinked
rows ARE kept -- this is a browsable list in its own right.

Delete-then-rebuild is scoped to (season, week) only -- NOT the whole table
like ingest_fantasypros.py/ingest_fantasypros_injuries.py -- since different
weeks and the ROS row coexist and don't supersede each other.

As of this writing, 2026 has no projections published yet (preseason, too
early -- confirmed live: count=0, players=null for both a week and ROS
request). That's expected, not a bug. Use --season 2025 to develop/verify
against real data until FantasyPros publishes 2026 numbers.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import time

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert

from app.db import get_sessionmaker
from app.fantasypros_client import RATE_LIMIT_SECONDS, fetch as _fetch, warn_if_capped as _warn_if_capped
from app.models import PlayerProjection
from scripts.ingest_fantasy_ranks import LINKABLE_POSITIONS, build_name_index

BOARD_POSITIONS = ["QB", "RB", "WR", "TE", "K", "DST"]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ingest FantasyPros weekly/ROS projections into player_projection.")
    p.add_argument("--season", type=int, required=True)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--week", type=int, choices=range(0, 19), help="0=preseason, 1-18=that week")
    group.add_argument("--ros", action="store_true", help="Rest-of-season projections")
    return p.parse_args()


async def ingest(season: int, week: int | None, ros: bool) -> None:
    week_value = None if ros else week
    label = "ROS" if ros else f"week {week}"

    sm = get_sessionmaker()
    async with sm() as session:
        name_index = await build_name_index(session, season)

        payload: list[dict] = []
        linked = unlinked = 0
        for i, position in enumerate(BOARD_POSITIONS):
            if i > 0:
                time.sleep(RATE_LIMIT_SECONDS)
            print(f"Fetching projections for {position} ({label})...")
            params: dict = {"position": position}
            if ros:
                params["ros"] = "true"
            else:
                params["week"] = week
            resp = _fetch(f"/{season}/projections", params)
            _warn_if_capped(resp)
            players = resp.get("players") or []
            print(f"  {len(players)} players")

            for p in players:
                name = (p.get("name") or "").strip()
                if not name:
                    continue
                position_id = (p.get("position_id") or position).upper()
                stats = p.get("stats") or {}

                gsis_id = None
                if position_id in LINKABLE_POSITIONS:
                    gsis_id = name_index.lookup(name, position_id)
                    if gsis_id:
                        linked += 1
                    else:
                        unlinked += 1

                payload.append(
                    {
                        "season": season,
                        "week": week_value,
                        "gsis_id": gsis_id,
                        "player_name": name[:128],
                        "team": (p.get("team_id") or "").strip()[:8] or None,
                        "position": position_id[:8],
                        "points": stats.get("points"),
                        "points_ppr": stats.get("points_ppr"),
                        "points_half": stats.get("points_half"),
                        "stats_json": json.dumps(stats),
                    }
                )

        total_linkable = linked + unlinked
        pct = (100 * linked / total_linkable) if total_linkable else 0
        print(f"Linked to player_dim: {linked}/{total_linkable} ({pct:.1f}%) — {unlinked} unlinked")

        await session.execute(
            delete(PlayerProjection).where(PlayerProjection.season == season, PlayerProjection.week == week_value)
        )
        for i in range(0, len(payload), 500):
            chunk = payload[i : i + 500]
            await session.execute(insert(PlayerProjection).values(chunk))
        await session.commit()

    print(f"Done — {len(payload)} rows written for {season} {label} (scoped rebuild).")


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(ingest(args.season, args.week, args.ros))
