"""
Weekly data refresh: re-pull schedules/scores, rebuild Elo ratings and game
predictions from the updated results, then re-scrape matchup comparison data
for whichever week is coming up next.

    python scripts/refresh_weekly.py

Chains ingest_schedules.ingest() + build_elo_ratings.main() +
scrape_matchup_stats.main() — see those modules for what each step actually
does. Meant to be the target of a recurring job (a Railway Cron Job service,
a plain cron entry, etc.) run weekly during the season, ideally after Monday
Night Football finishes so every game for the week has a final score. See
DEPLOYMENT.md's "Keeping Data Fresh" section for how to wire that up.

Only the *upcoming* week gets re-scraped for matchup data, not the whole
season — TeamRankings' comparison numbers shift to reflect current-season
form as the year goes on, so scraping every week every time would mostly
just re-fetch pages that haven't meaningfully changed since last week, while
missing the point of a weekly job (catching the ones that *have* changed:
the week that's about to happen). See scripts/scrape_matchup_stats.py for a
one-off full-season scrape instead.
"""
from __future__ import annotations

import asyncio
from datetime import date

from sqlalchemy import select

from app.db import get_sessionmaker
from app.models import Game
from scripts.build_elo_ratings import main as build_elo_ratings
from scripts.ingest_schedules import ingest as ingest_schedules
from scripts.scrape_matchup_stats import main as scrape_matchup_stats


async def _upcoming_slate(session) -> tuple[int, int] | None:
    """Same "next slate" logic as api_picks.py's _resolve_slate: the
    earliest not-yet-played game, or None once the season's fully over."""
    row = (
        await session.execute(
            select(Game.season, Game.week)
            .where(Game.gameday.is_not(None), Game.gameday >= date.today())
            .order_by(Game.gameday, Game.game_id)
            .limit(1)
        )
    ).first()
    return (row[0], row[1]) if row else None


async def main() -> None:
    print("== Refreshing schedules/scores ==")
    await ingest_schedules(csv_path=None, from_year=1999, to_year=2100)

    print("\n== Rebuilding Elo ratings + predictions ==")
    await build_elo_ratings()

    print("\n== Refreshing matchup data for the upcoming week ==")
    sm = get_sessionmaker()
    async with sm() as session:
        slate = await _upcoming_slate(session)
    if slate is None:
        print("No upcoming games found — skipping.")
    else:
        season, week = slate
        await scrape_matchup_stats(season, week, None)


if __name__ == "__main__":
    asyncio.run(main())
