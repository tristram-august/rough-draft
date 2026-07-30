"""
Ingest a preseason fantasy draft board (players.json) into `fantasy_rank`.

    python scripts/ingest_fantasy_ranks.py --json ./data/fantasy/players_2026.json --season 2026

Expects the FantasyPros-style export shape:
    {rk, tier, name, team, pos, posRank, bye, sos, ecrAdp, avgDiff}

"-" is used as the null sentinel for ecrAdp/avgDiff. Free agents carry team "FA"
and null bye/sos.

Player names are matched to player_dim on a normalized key (case, punctuation and
generational suffixes stripped) so a board row can link to production history.
Exact-string matching drops a meaningful slice of rows — see the OL stats ingest
for what that costs. Unmatched rows still import; they just don't link.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.db import get_sessionmaker
from app.models import FantasyRank, PlayerDim

# Positions that exist in player_dim. DST rows are team names, not people.
LINKABLE_POSITIONS = {"QB", "RB", "WR", "TE", "K"}

_SUFFIXES = re.compile(r"\b(jr|sr|ii|iii|iv|v)\b")
_NON_ALPHA = re.compile(r"[^a-z ]")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ingest a fantasy draft board JSON into fantasy_rank.")
    p.add_argument("--json", type=Path, required=True, help="Path to players.json")
    p.add_argument("--season", type=int, required=True, help="Season the board is for (e.g. 2026)")
    return p.parse_args()


def norm_name(name: str) -> str:
    """Lowercase, drop punctuation and Jr/III-style suffixes, collapse spaces."""
    out = _NON_ALPHA.sub(" ", (name or "").lower())
    out = _SUFFIXES.sub(" ", out)
    return " ".join(out.split())


def _int(val: object) -> int | None:
    """Handles ints, "+15"/"-8" strings, and the "-" null sentinel."""
    if val is None:
        return None
    text = str(val).strip().replace("+", "")
    if text in ("", "-"):
        return None
    try:
        return int(float(text))
    except (ValueError, TypeError):
        return None


def _float(val: object) -> float | None:
    if val is None:
        return None
    text = str(val).strip().replace("+", "")
    if text in ("", "-"):
        return None
    try:
        return float(text)
    except (ValueError, TypeError):
        return None


class NameIndex:
    """
    Resolves a board name to a gsis_id.

    Two things make a naive (name, position) lookup miss real players:
      - Father/son pairs collide once suffixes are normalized away
        (Marvin Harrison / Marvin Harrison Jr. are both WRs).
      - Players change positions; Juwan Johnson is a WR in player_dim and a
        TE on the board.

    So collisions are broken by who was actually playing in the board's season,
    and a name-only lookup backstops position drift. Anything still ambiguous
    stays unlinked rather than guessed.
    """

    def __init__(self, season: int) -> None:
        self.season = season
        self._by_key: dict[tuple[str, str], list[tuple[str, int | None]]] = {}
        self._by_name: dict[str, list[tuple[str, int | None]]] = {}

    def add(self, gsis_id: str, display_name: str, position: str | None, last_season: int | None) -> None:
        norm = norm_name(display_name)
        self._by_key.setdefault((norm, (position or "").upper()), []).append((gsis_id, last_season))
        self._by_name.setdefault(norm, []).append((gsis_id, last_season))

    def _resolve(self, candidates: list[tuple[str, int | None]]) -> str | None:
        unique = {gsis_id for gsis_id, _ in candidates}
        if len(unique) == 1:
            return candidates[0][0]
        # Prefer whoever was still active for this board's season.
        active = [c for c in candidates if c[1] is not None and c[1] >= self.season - 1]
        if len({gsis_id for gsis_id, _ in active}) == 1:
            return active[0][0]
        return None

    def lookup(self, name: str, position: str) -> str | None:
        norm = norm_name(name)
        hit = self._resolve(self._by_key.get((norm, position.upper()), []))
        if hit:
            return hit
        return self._resolve(self._by_name.get(norm, []))


async def build_name_index(session, season: int) -> NameIndex:
    rows = (
        await session.execute(
            select(
                PlayerDim.gsis_id,
                PlayerDim.display_name,
                PlayerDim.position,
                PlayerDim.last_season,
            ).where(PlayerDim.display_name.is_not(None))
        )
    ).all()

    index = NameIndex(season)
    for gsis_id, display_name, position, last_season in rows:
        index.add(gsis_id, display_name, position, last_season)
    return index


async def ingest(json_path: Path, season: int) -> None:
    players = json.loads(json_path.read_text(encoding="utf-8"))
    print(f"JSON: {len(players)} players for season {season}")

    sm = get_sessionmaker()
    async with sm() as session:
        name_index = await build_name_index(session, season)

        payload: list[dict] = []
        linked = unlinked = 0
        for p in players:
            position = (p.get("pos") or "").upper()
            name = (p.get("name") or "").strip()
            if not name:
                continue

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
                    "overall_rank": _int(p.get("rk")) or 0,
                    "tier": _int(p.get("tier")),
                    "player_name": name[:128],
                    "team": (p.get("team") or "").strip()[:8] or None,
                    "position": position[:8],
                    "position_rank": _int(p.get("posRank")),
                    "bye_week": _int(p.get("bye")),
                    "sos": _int(p.get("sos")),
                    "ecr_vs_adp": _int(p.get("ecrAdp")),
                    "avg_diff": _float(p.get("avgDiff")),
                    "gsis_id": gsis_id,
                }
            )

        total_linkable = linked + unlinked
        pct = (100 * linked / total_linkable) if total_linkable else 0
        print(f"Linked to player_dim: {linked}/{total_linkable} ({pct:.1f}%) — {unlinked} unlinked")

        for i in range(0, len(payload), 500):
            chunk = payload[i : i + 500]
            stmt = insert(FantasyRank).values(chunk)
            stmt = stmt.on_conflict_do_update(
                index_elements=["season", "overall_rank"],
                set_={
                    c.name: stmt.excluded[c.name]
                    for c in FantasyRank.__table__.columns
                    if c.name not in ("id", "season", "overall_rank")
                },
            )
            await session.execute(stmt)
        await session.commit()

    print(f"Done — {len(payload)} rows upserted for {season}.")


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(ingest(args.json, args.season))
