"""
Scrape TeamRankings.com team-comparison tables and load them into
`matchup_stat` — the data behind the "Matchup" panel on the picks board
(app/ui/matchup-stats-button.tsx).

    python3 -m scripts.scrape_matchup_stats --season 2026 --week 1
    python3 -m scripts.scrape_matchup_stats --season 2026   # every week

Combines what used to be two manual steps (a throwaway scraper + this repo's
scripts/ingest_matchup_stats.py) into one, and derives the matchups straight
from the `game` table instead of a hand-typed list. Stdlib-only (no
pandas/lxml/requests) since `pip install` for those hits an SSL cert issue in
some environments this needs to run in.

--stat-season is which season the stat VALUES describe (defaults to
season - 1, e.g. a week 1 2026 game gets 2025 full-season numbers, since
that's the most recent complete season). Important: TeamRankings' own pages
update to reflect *current-season* form once games start being played, so a
week 10 page scraped in the preseason (still showing 2025 numbers) will look
different from the same page scraped once 2026 is actually underway. A
one-time full-season scrape is a reasonable placeholder for weeks far out,
but it goes stale the moment real 2026 results exist — see
scripts/refresh_weekly.py, which re-scrapes just the upcoming week on a
schedule so each week's data is current by the time anyone plays it.

Respects TeamRankings' robots.txt (Crawl-delay: 10) — one request per game
(each game's page has all 12 tables). A 16-game week is ~3 minutes; a full
18-week season is ~270 games, roughly 45 minutes end to end.
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


async def main(season: int, week: int | None, stat_season: int | None) -> None:
    """week=None scrapes every week the schedule has for that season. Each
    week is ingested right after it's scraped (not batched to the end) so a
    multi-hour full-season run doesn't lose everything to one dropped
    connection partway through — only whatever week was mid-scrape is lost.

    Crawl-delay is paced across the *whole* run, not reset per week, since
    it's really one continuous sequence of requests to the same host."""
    sm = get_sessionmaker()
    async with sm() as session:
        if week is not None:
            weeks = [week]
        else:
            weeks = sorted(
                (
                    await session.execute(
                        select(Game.week)
                        .where(Game.season == season, Game.week.is_not(None))
                        .distinct()
                    )
                ).scalars()
            )

        games_by_week = {}
        for w in weeks:
            games_by_week[w] = (
                await session.execute(
                    select(Game.away_team, Game.home_team).where(Game.season == season, Game.week == w)
                )
            ).all()

    if not any(games_by_week.values()):
        print(f"No games found for season={season} — check the schedule is ingested.")
        return

    resolved_stat_season = stat_season if stat_season is not None else season - 1
    total_games = sum(len(g) for g in games_by_week.values())
    print(f"Scraping {total_games} games across {len(weeks)} week(s) for season={season}, stat_season={resolved_stat_season}...")

    scraped = 0
    for w in weeks:
        games = games_by_week[w]
        if not games:
            continue
        print(f"\n-- Week {w}: {len(games)} games --")
        with TemporaryDirectory(prefix=f"matchup_stats_wk{w}_") as tmp:
            out_dir = Path(tmp)
            total_errors = 0
            for away, home in games:
                if scraped > 0:
                    time.sleep(CRAWL_DELAY_SECONDS)
                scraped += 1
                result = scrape_game(away, home, w, season, out_dir)
                errors = [r for r in result if r.startswith("ERROR")]
                total_errors += len(errors)
                print(f"  {away}@{home}: {len(result) - len(errors)} files, {len(errors)} errors")
                for e in errors:
                    print(f"    {e}")
            if total_errors:
                print(f"  {total_errors} scrape errors in week {w} — ingesting whatever did succeed.")
            await ingest(out_dir, resolved_stat_season)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--season", type=int, required=True)
    p.add_argument("--week", type=int, default=None, help="Omit to scrape every week in the season")
    p.add_argument("--stat-season", type=int, default=None, help="Defaults to season - 1")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(main(args.season, args.week, args.stat_season))
