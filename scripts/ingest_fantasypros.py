"""
Pull a live fantasy draft board from the FantasyPros public API into
`fantasy_rank`, replacing the manual JSON-export workflow in
ingest_fantasy_ranks.py.

    python scripts/ingest_fantasypros.py --season 2026

Requires FANTASYPROS_API_KEY (see app/settings.py / .env). The free tier caps
every response at 10 rows regardless of the real count — this script needs a
paid plan that returns full responses (confirmed via "tier" in the JSON body;
see ROADMAP.md for that whole saga).

Two kinds of calls, 1/second to stay under the plan's rate limit:
  - GET /nfl/players (once) -- the only endpoint with a true cross-position
    overall rank (rank_ecr_ppr) and ADP (rank_adp_ppr) in one place.
  - GET /nfl/{season}/consensus-rankings?position=X&scoring=PPR, once per
    position in BOARD_POSITIONS -- gives tier, position rank (as "RB1" etc),
    and bye week, none of which /players exposes.

Merged on FantasyPros' own numeric player_id (exact, no name-matching needed
between our two calls). `overall_rank` comes from /players' rank_ecr_ppr;
rows that don't resolve to one are skipped rather than guessed, since
overall_rank is UNIQUE per (season, overall_rank).

The API's rank numbering has no relationship to whatever a prior CSV import
(or a prior run of this script) used, so this is a full delete-then-insert
per season, not an upsert -- an upsert keyed on (season, overall_rank) would
leave old ranks 1..N sitting alongside new ranks 1..M with the same players
duplicated under two different numbers. Same "rebuild from scratch" call as
build_elo_ratings.py, for the same reason.

`sos` and `avg_diff` aren't exposed by this API at all (they're proprietary
Draft Wizard export fields) and are left null, same as any row the old CSV
importer left unset for other reasons.

Player-name linking to player_dim reuses ingest_fantasy_ranks.py's NameIndex
unchanged.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert

from app.db import get_sessionmaker
from app.models import FantasyRank
from app.settings import settings
from scripts.ingest_fantasy_ranks import LINKABLE_POSITIONS, build_name_index

API_BASE = "https://api.fantasypros.com/public/v2/json/nfl"
BOARD_POSITIONS = ["QB", "RB", "WR", "TE", "K", "DST"]
RATE_LIMIT_SECONDS = 1.1  # premium plan is 1 req/sec; leave a little headroom

_POS_RANK_RE = re.compile(r"^[A-Z]+(\d+)$")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ingest a live FantasyPros board into fantasy_rank.")
    p.add_argument("--season", type=int, required=True, help="Season the board is for (e.g. 2026)")
    p.add_argument("--scoring", default="PPR", choices=["STD", "PPR", "HALF"])
    return p.parse_args()


def _fetch(path: str, params: dict) -> dict:
    if not settings.fantasypros_api_key:
        raise SystemExit("FANTASYPROS_API_KEY is not set (see .env / app/settings.py)")
    qs = urllib.parse.urlencode(params)
    url = f"{API_BASE}{path}?{qs}" if qs else f"{API_BASE}{path}"
    req = urllib.request.Request(url, headers={"x-api-key": settings.fantasypros_api_key})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"FantasyPros API error {e.code} on {path}: {body}") from e


def _int_or_none(val: object) -> int | None:
    text = str(val or "").strip()
    return int(text) if text.isdigit() else None


def _pos_rank_number(pos_rank: str | None) -> int | None:
    m = _POS_RANK_RE.match(pos_rank or "")
    return int(m.group(1)) if m else None


async def ingest(season: int, scoring: str) -> None:
    print("Fetching /players (overall ECR + ADP)...")
    players_resp = _fetch("/players", {})
    _warn_if_capped(players_resp)
    overall_by_id = {
        p["player_id"]: (p.get("rank_ecr_ppr"), p.get("rank_adp_ppr"))
        for p in players_resp["players"]
        if p.get("rank_ecr_ppr")
    }
    print(f"  {len(overall_by_id)} players with an overall ECR")

    board_rows: dict[int, dict] = {}
    for i, position in enumerate(BOARD_POSITIONS):
        if i > 0:
            time.sleep(RATE_LIMIT_SECONDS)
        print(f"Fetching consensus-rankings for {position}...")
        resp = _fetch(f"/{season}/consensus-rankings", {"position": position, "scoring": scoring})
        _warn_if_capped(resp)
        for p in resp["players"]:
            board_rows[p["player_id"]] = p
        print(f"  {len(resp['players'])} players")

    sm = get_sessionmaker()
    async with sm() as session:
        name_index = await build_name_index(session, season)

        payload: list[dict] = []
        linked = unlinked = skipped_no_overall = 0
        for player_id, p in board_rows.items():
            position = (p.get("player_position_id") or "").upper()
            name = (p.get("player_name") or "").strip()
            if not name:
                continue

            overall = overall_by_id.get(player_id)
            if overall is None or overall[0] is None:
                skipped_no_overall += 1
                continue
            overall_rank, adp = overall
            ecr_vs_adp = (adp - overall_rank) if isinstance(adp, int) else None

            gsis_id = None
            if position in LINKABLE_POSITIONS:
                gsis_id = name_index.lookup(name, position)
                if gsis_id:
                    linked += 1
                else:
                    unlinked += 1

            payload.append(
                {
                    "season": season,
                    "overall_rank": overall_rank,
                    "tier": p.get("tier"),
                    "player_name": name[:128],
                    "team": (p.get("player_team_id") or "").strip()[:8] or None,
                    "position": position[:8],
                    "position_rank": _pos_rank_number(p.get("pos_rank")),
                    "bye_week": _int_or_none(p.get("player_bye_week")),
                    "sos": None,
                    "ecr_vs_adp": ecr_vs_adp,
                    "avg_diff": None,
                    "gsis_id": gsis_id,
                }
            )

        total_linkable = linked + unlinked
        pct = (100 * linked / total_linkable) if total_linkable else 0
        print(f"Linked to player_dim: {linked}/{total_linkable} ({pct:.1f}%) — {unlinked} unlinked")
        if skipped_no_overall:
            print(f"Skipped {skipped_no_overall} board rows with no overall ECR in /players")

        await session.execute(delete(FantasyRank).where(FantasyRank.season == season))
        for i in range(0, len(payload), 500):
            chunk = payload[i : i + 500]
            await session.execute(insert(FantasyRank).values(chunk))
        await session.commit()

    print(f"Done — {len(payload)} rows written for {season} (full rebuild).")


def _warn_if_capped(resp: dict) -> None:
    if resp.get("public_api_limited") and resp.get("limit"):
        print(f"  WARNING: response capped at {resp['limit']} rows (tier={resp.get('tier')}) — "
              f"got {len(resp.get('players', []))} of {resp.get('count')}")


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(ingest(args.season, args.scoring))
