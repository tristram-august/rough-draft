"""
Ingest scraped team-comparison CSVs into `matchup_stat`.

    python scripts/ingest_matchup_stats.py --dir ./matchup-stats/week-1 --stat-season 2025

Expects filenames shaped like the scraper's output:
    matchup_{away-slug}-{home-slug}-week-{week}-{season}_{Home|Visitor}_{Category}.csv

e.g. matchup_patriots-seahawks-week-1-2026_Home_Overall.csv — a week 1 2026
game (NE @ SEA), "Home" file (Seattle's own stats vs. what New England allows),
Overall category. Each CSV row is one stat:

    SEA,Value (rank),Value (rank).1,NE
    Points/Game,29.2 (#2),17.9 (#3),Opp Points/Game

--stat-season is which season the STAT VALUES describe (e.g. 2025, the most
recent complete season), independent of the game's own season/week in the
filename. There's no way to derive it from the file, so it's a required flag.

game_id is resolved by looking up (season, week, away_team, home_team) against
the `game` table rather than building "{season}_{week:02d}_{away}_{home}" by
hand — nflverse's own game_id string sometimes keeps its original team code
even where the away_team/home_team columns were aliased to the current one
(the Rams are LAR in those columns but still "LA" inside some game_ids), so a
hand-built id can miss a real row. A matchup with no corresponding schedule
row is skipped with a clear reason, not silently dropped.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import io
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.db import get_sessionmaker
from app.models import Game, MatchupStat

# The scraped page uses nflverse-era codes in places (e.g. "LA" for the Rams)
# that differ from the current franchise abbreviation used everywhere else on
# this site (team colors, the game table's own away_team/home_team columns).
# Same drift as scripts/ingest_schedules.py; applied here too so a team's rows
# always carry the abbreviation the rest of the site expects.
ABBREV_ALIASES = {"LA": "LAR", "STL": "LAR", "OAK": "LV", "SD": "LAC"}


def normalize_abbrev(abbrev: str) -> str:
    return ABBREV_ALIASES.get(abbrev, abbrev)


NAME_TO_ABBREV = {
    "cardinals": "ARI", "falcons": "ATL", "ravens": "BAL", "bills": "BUF",
    "panthers": "CAR", "bears": "CHI", "bengals": "CIN", "browns": "CLE",
    "cowboys": "DAL", "broncos": "DEN", "lions": "DET", "packers": "GB",
    "texans": "HOU", "colts": "IND", "jaguars": "JAX", "chiefs": "KC",
    "chargers": "LAC", "rams": "LAR", "raiders": "LV", "dolphins": "MIA",
    "vikings": "MIN", "patriots": "NE", "saints": "NO", "giants": "NYG",
    "jets": "NYJ", "eagles": "PHI", "steelers": "PIT", "49ers": "SF",
    "niners": "SF", "seahawks": "SEA", "buccaneers": "TB", "bucs": "TB",
    "titans": "TEN", "commanders": "WAS", "redskins": "WAS", "football team": "WAS",
}

FILENAME_RE = re.compile(
    r"^matchup_(?P<away>[a-z0-9]+)-(?P<home>[a-z0-9]+)-week-(?P<week>\d+)-(?P<season>\d+)"
    r"_(?P<perspective>Home|Visitor)_(?P<category>[A-Za-z]+)\.csv$",
    re.IGNORECASE,
)

VALUE_RANK_RE = re.compile(r"^(?P<value>.+?)\s*\(#(?P<rank>\d+)\)\s*$")


def parse_value(raw: str) -> tuple[str, int | None]:
    """"29.2 (#2)" -> ("29.2", 2). Falls back to (raw, None) if unranked."""
    raw = raw.strip()
    m = VALUE_RANK_RE.match(raw)
    if not m:
        return raw, None
    return m.group("value"), int(m.group("rank"))


def resolve_abbrev(slug: str) -> str | None:
    return NAME_TO_ABBREV.get(slug.lower().replace("-", " "))


def parse_filename(path: Path) -> dict | None:
    m = FILENAME_RE.match(path.name)
    if not m:
        return None
    away = resolve_abbrev(m.group("away"))
    home = resolve_abbrev(m.group("home"))
    if away is None or home is None:
        return None
    season, week = int(m.group("season")), int(m.group("week"))
    return {
        "away": away,
        "home": home,
        "season": season,
        "week": week,
        "perspective": m.group("perspective"),
        "category": m.group("category"),
    }


def parse_csv_rows(text: str) -> list[dict]:
    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)
    if not header or len(header) < 4:
        return []
    team_abbrev = normalize_abbrev(header[0].strip().upper())

    rows = []
    for row in reader:
        if len(row) < 4 or not row[0].strip():
            continue
        stat_label = row[0].strip()
        team_value, team_rank = parse_value(row[1])
        opp_value, opp_rank = parse_value(row[2])
        opp_label = row[3].strip()
        rows.append(
            {
                "team": team_abbrev,
                "stat_label": stat_label,
                "team_value": team_value,
                "team_rank": team_rank,
                "opp_value": opp_value,
                "opp_rank": opp_rank,
                "opp_stat_label": opp_label,
            }
        )
    return rows


async def ingest(directory: Path, stat_season: int) -> None:
    files = sorted(directory.glob("matchup_*.csv"))
    print(f"Found {len(files)} matchup CSVs in {directory}")

    sm = get_sessionmaker()
    async with sm() as session:
        schedule_rows = (
            await session.execute(select(Game.game_id, Game.season, Game.week, Game.away_team, Game.home_team))
        ).all()
        game_id_by_matchup = {
            (season, week, away, home): game_id for game_id, season, week, away, home in schedule_rows
        }

        payload: list[dict] = []
        skipped_unparsed: list[str] = []
        skipped_no_game: list[str] = []

        for path in files:
            meta = parse_filename(path)
            if meta is None:
                skipped_unparsed.append(path.name)
                continue
            game_id = game_id_by_matchup.get((meta["season"], meta["week"], meta["away"], meta["home"]))
            if game_id is None:
                skipped_no_game.append(
                    f"{path.name}  (no schedule row for {meta['away']}@{meta['home']}, "
                    f"season={meta['season']} week={meta['week']})"
                )
                continue

            rows = parse_csv_rows(path.read_text(encoding="utf-8"))
            opp_abbrev = meta["home"] if meta["perspective"] == "Visitor" else meta["away"]
            for r in rows:
                payload.append(
                    {
                        "game_id": game_id,
                        "category": meta["category"],
                        "stat_label": r["stat_label"],
                        "team": r["team"],
                        "team_value": r["team_value"],
                        "team_rank": r["team_rank"],
                        "opp_team": opp_abbrev,
                        "opp_stat_label": r["opp_stat_label"],
                        "opp_value": r["opp_value"],
                        "opp_rank": r["opp_rank"],
                        "source_season": stat_season,
                    }
                )

        if skipped_unparsed:
            print(f"\nSkipped (filename didn't match the expected pattern): {len(skipped_unparsed)}")
            for name in skipped_unparsed[:10]:
                print(f"  {name}")
        if skipped_no_game:
            print(f"\nSkipped (no matching game in the schedule): {len(skipped_no_game)}")
            for name in skipped_no_game[:10]:
                print(f"  {name}")

        print(f"\n{len(payload)} stat rows parsed from {len(files) - len(skipped_unparsed) - len(skipped_no_game)} files")
        if not payload:
            print("Nothing to write.")
            return

        for i in range(0, len(payload), 500):
            chunk = payload[i : i + 500]
            stmt = insert(MatchupStat).values(chunk)
            stmt = stmt.on_conflict_do_update(
                index_elements=["game_id", "category", "stat_label", "team"],
                set_={
                    c.name: stmt.excluded[c.name]
                    for c in MatchupStat.__table__.columns
                    if c.name not in ("id", "game_id", "category", "stat_label", "team")
                },
            )
            await session.execute(stmt)
        await session.commit()
        print(f"Committed {len(payload)} rows.")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dir", type=Path, required=True, help="Directory of matchup_*.csv files")
    p.add_argument("--stat-season", type=int, required=True, help="Season the stat VALUES are from, e.g. 2025")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(ingest(args.dir, args.stat_season))
