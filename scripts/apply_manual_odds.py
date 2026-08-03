"""
Manually apply spreads to the `game` table from a pasted odds sheet, until
there's a live odds feed. Only touches spread_line — gameday/gametime/weekday
already come from the schedule ingest and are treated as correct.

Usage:
    python scripts/apply_manual_odds.py --season 2026 --week 1 --file odds.txt

Input format, one game per line (tabs or 2+ spaces between the matchup and the
day/time — the day/time column is ignored, kept only for readability):

    New England at Seattle (-3.5)      Wed 8:20pm
    Buffalo (-1.5) at Houston          Sun 1:00pm

The favorite can appear on either team and the line can say "at" or "vs." —
home/away isn't inferred from that wording (this sheet is inconsistent about
it). Instead each line resolves to an unordered team pair + which one is
favored, then matches against the real home_team/away_team already in the DB
to compute spread_line with the correct sign.
"""
from __future__ import annotations

import argparse
import asyncio
import re
from pathlib import Path

from sqlalchemy import select

from app.db import get_sessionmaker
from app.models import Game

NAME_TO_ABBREV = {
    "arizona": "ARI", "atlanta": "ATL", "baltimore": "BAL", "buffalo": "BUF",
    "carolina": "CAR", "chicago": "CHI", "cincinnati": "CIN", "cleveland": "CLE",
    "dallas": "DAL", "denver": "DEN", "detroit": "DET", "green bay": "GB",
    "houston": "HOU", "indianapolis": "IND", "jacksonville": "JAX", "kansas city": "KC",
    "la chargers": "LAC", "los angeles chargers": "LAC", "chargers": "LAC",
    "la rams": "LAR", "los angeles rams": "LAR", "rams": "LAR",
    "las vegas": "LV", "miami": "MIA", "minnesota": "MIN",
    "new england": "NE", "new orleans": "NO",
    "ny giants": "NYG", "new york giants": "NYG", "giants": "NYG",
    "ny jets": "NYJ", "new york jets": "NYJ", "jets": "NYJ",
    "philadelphia": "PHI", "pittsburgh": "PIT", "san francisco": "SF",
    "seattle": "SEA", "tampa bay": "TB", "tennessee": "TEN", "washington": "WAS",
}

LINE_RE = re.compile(
    r"^(?P<a>[A-Za-z .]+?)"
    r"(?:\s*\((?P<fav_a>-[\d.]+)\))?"
    r"\s+(?:at|vs\.?)\s+"
    r"(?P<b>[A-Za-z .]+?)"
    r"(?:\s*\((?P<fav_b>-[\d.]+)\))?"
    r"(?:\t|  +).*$"
)


def parse_paste(text: str) -> list[dict]:
    games = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        m = LINE_RE.match(line)
        if not m:
            raise SystemExit(f"Couldn't parse line: {raw_line!r}")

        a_name, b_name = m.group("a").strip().lower(), m.group("b").strip().lower()
        if a_name not in NAME_TO_ABBREV:
            raise SystemExit(f"Unknown team name {a_name!r} in line: {raw_line!r}")
        if b_name not in NAME_TO_ABBREV:
            raise SystemExit(f"Unknown team name {b_name!r} in line: {raw_line!r}")
        a_abbr, b_abbr = NAME_TO_ABBREV[a_name], NAME_TO_ABBREV[b_name]

        fav_a, fav_b = m.group("fav_a"), m.group("fav_b")
        if bool(fav_a) == bool(fav_b):
            raise SystemExit(f"Expected exactly one favorite marked in line: {raw_line!r}")
        favored, magnitude = (a_abbr, abs(float(fav_a))) if fav_a else (b_abbr, abs(float(fav_b)))

        games.append({"teams": {a_abbr, b_abbr}, "favored": favored, "magnitude": magnitude, "raw": raw_line})
    return games


async def apply_odds(season: int, week: int, text: str) -> None:
    parsed = parse_paste(text)
    print(f"Parsed {len(parsed)} games from the paste.")

    sm = get_sessionmaker()
    async with sm() as session:
        rows = (
            await session.execute(select(Game).where(Game.season == season, Game.week == week))
        ).scalars().all()
        by_pair = {frozenset({g.away_team, g.home_team}): g for g in rows}

        updates: list[tuple[Game, float]] = []
        for p in parsed:
            game = by_pair.get(frozenset(p["teams"]))
            if game is None:
                print(f"  NO DB MATCH: {p['raw']!r} (looked for {sorted(p['teams'])})")
                continue
            new_spread = p["magnitude"] if p["favored"] == game.home_team else -p["magnitude"]
            changed = "" if game.spread_line == new_spread else "  <- CHANGED"
            print(
                f"  {game.away_team:4s}@{game.home_team:4s}  "
                f"db={game.spread_line!s:>6}  new={new_spread!s:>6}{changed}"
            )
            updates.append((game, new_spread))

        if len(updates) != len(parsed):
            print(f"\n{len(parsed) - len(updates)} line(s) had no DB match — aborting, no writes made.")
            return

        for game, new_spread in updates:
            game.spread_line = new_spread
        await session.commit()
        print(f"\nCommitted spread_line for {len(updates)} games.")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--season", type=int, required=True)
    p.add_argument("--week", type=int, required=True)
    p.add_argument("--file", type=Path, required=True, help="Path to the pasted odds sheet")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(apply_odds(args.season, args.week, args.file.read_text(encoding="utf-8")))
