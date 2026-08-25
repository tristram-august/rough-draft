"""
Scrape TeamRankings.com team-comparison tables for one week's games and load
them into `matchup_stat` — the data behind the "Matchup" panel on the picks
board (app/ui/matchup-stats-button.tsx).

    python3 -m scripts.scrape_matchup_stats --season 2026 --week 1

Combines what used to be two manual steps (a throwaway scraper + this repo's
scripts/ingest_matchup_stats.py) into one, and derives the matchups straight
from the `game` table instead of a hand-typed list, so any future week is
just a different --week value. Stdlib-only (no pandas/lxml/requests) since
`pip install` for those hits an SSL cert issue in some environments this
needs to run in.

--stat-season is which season the stat VALUES describe (defaults to
season - 1, e.g. a week 1 2026 game gets 2025 full-season numbers, since
that's the most recent complete season) -- override if TeamRankings starts
publishing in-season numbers instead once 2026 itself has games played.

Respects TeamRankings' robots.txt (Crawl-delay: 10) — one request per game
(each game's page has all 12 tables), so a 16-game week is ~16 requests,
roughly 3 minutes end to end including the delay.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import io
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import select

from app.db import get_sessionmaker
from app.models import Game
from scripts.ingest_matchup_stats import ingest

# Confirmed against real TeamRankings URLs (all 16 week-1 2026 games scraped
# successfully with these) rather than guessed from the roster nickname —
# a few teams (Washington, Tampa Bay, the Rams/49ers) have had multiple
# nicknames/relocations, so "derive it from the abbrev" isn't reliable.
ABBREV_TO_SLUG = {
    "ARI": "cardinals", "ATL": "falcons", "BAL": "ravens", "BUF": "bills",
    "CAR": "panthers", "CHI": "bears", "CIN": "bengals", "CLE": "browns",
    "DAL": "cowboys", "DEN": "broncos", "DET": "lions", "GB": "packers",
    "HOU": "texans", "IND": "colts", "JAX": "jaguars", "KC": "chiefs",
    "LAC": "chargers", "LAR": "rams", "LV": "raiders", "MIA": "dolphins",
    "MIN": "vikings", "NE": "patriots", "NO": "saints", "NYG": "giants",
    "NYJ": "jets", "PHI": "eagles", "PIT": "steelers", "SF": "49ers",
    "SEA": "seahawks", "TB": "buccaneers", "TEN": "titans", "WAS": "commanders",
}

CATEGORY_DICT = {
    0: "Visitor_Overall", 1: "Home_Overall",
    2: "Visitor_Rushing", 3: "Home_Rushing",
    4: "Visitor_Passing", 5: "Home_Passing",
    6: "Visitor_Kicking", 7: "Home_Kicking",
    8: "Visitor_Turnovers", 9: "Home_Turnovers",
    10: "Visitor_Penalties", 11: "Home_Penalties",
}

CRAWL_DELAY_SECONDS = 10


class TableExtractor(HTMLParser):
    """Pulls every <table class="tr-table ..."> on the page, in document
    order, as a list of rows of cell text (nested tags flattened)."""

    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._in_table = 0
        self._in_cell = False
        self._row: list[str] | None = None
        self._table: list[list[str]] | None = None
        self._cell_buf: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_dict = dict(attrs)
        if tag == "table":
            classes = (attr_dict.get("class") or "").split()
            if "tr-table" in classes:
                self._in_table = 1
                self._table = []
            elif self._in_table:
                self._in_table += 1
        elif self._in_table and tag == "tr":
            self._row = []
        elif self._in_table and tag in ("td", "th"):
            self._in_cell = True
            self._cell_buf = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "table" and self._in_table:
            self._in_table -= 1
            if self._in_table == 0 and self._table is not None:
                self.tables.append(self._table)
                self._table = None
        elif self._in_table and tag == "tr" and self._row is not None:
            if self._table is not None:
                self._table.append(self._row)
            self._row = None
        elif self._in_table and tag in ("td", "th") and self._in_cell:
            text = " ".join("".join(self._cell_buf).split())
            if self._row is not None:
                self._row.append(text)
            self._in_cell = False

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cell_buf.append(data)


def _fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "roughdraftfootball.com"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", "replace")


def _rows_to_csv(header: list[str], rows: list[list[str]]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    w.writerows(rows)
    return buf.getvalue()


def scrape_game(away: str, home: str, week: int, season: int, out_dir: Path) -> list[str]:
    """Returns filenames written, or a single 'ERROR: ...' entry on failure."""
    away_slug, home_slug = ABBREV_TO_SLUG.get(away), ABBREV_TO_SLUG.get(home)
    if not away_slug or not home_slug:
        return [f"ERROR: no TeamRankings slug for {away} or {home}"]

    slug = f"{away_slug}-{home_slug}"
    url = f"https://www.teamrankings.com/nfl/matchup/{slug}-week-{week}-{season}/stats"
    try:
        html = _fetch(url)
    except (urllib.error.URLError, TimeoutError) as e:
        return [f"ERROR: {slug}: fetch failed: {e}"]

    parser = TableExtractor()
    parser.feed(html)
    if len(parser.tables) < 12:
        return [f"ERROR: {slug}: expected >=12 tables, got {len(parser.tables)} (page layout may have changed)"]

    written = []
    for i, table in enumerate(parser.tables[:12]):
        if not table:
            continue
        header, rows = table[0], table[1:]
        if len(header) != 4:
            written.append(f"ERROR: {slug} table {i}: header has {len(header)} cols, expected 4")
            continue
        filename = f"matchup_{slug}-week-{week}-{season}_{CATEGORY_DICT[i]}.csv"
        (out_dir / filename).write_text(_rows_to_csv(header, rows), encoding="utf-8")
        written.append(filename)
    return written


async def main(season: int, week: int, stat_season: int | None) -> None:
    sm = get_sessionmaker()
    async with sm() as session:
        games = (
            await session.execute(
                select(Game.away_team, Game.home_team).where(Game.season == season, Game.week == week)
            )
        ).all()

    if not games:
        print(f"No games found for season={season} week={week} — check the schedule is ingested.")
        return

    print(f"Scraping {len(games)} games for season={season} week={week}...")
    with TemporaryDirectory(prefix="matchup_stats_") as tmp:
        out_dir = Path(tmp)
        total_errors = 0
        for i, (away, home) in enumerate(games):
            result = scrape_game(away, home, week, season, out_dir)
            errors = [r for r in result if r.startswith("ERROR")]
            total_errors += len(errors)
            print(f"  {away}@{home}: {len(result) - len(errors)} files, {len(errors)} errors")
            for e in errors:
                print(f"    {e}")
            if i < len(games) - 1:
                time.sleep(CRAWL_DELAY_SECONDS)

        if total_errors:
            print(f"\n{total_errors} scrape errors — ingesting whatever did succeed.")

        await ingest(out_dir, stat_season if stat_season is not None else season - 1)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--season", type=int, required=True)
    p.add_argument("--week", type=int, required=True)
    p.add_argument("--stat-season", type=int, default=None, help="Defaults to season - 1")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(main(args.season, args.week, args.stat_season))
