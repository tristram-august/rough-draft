"""
Weekly data refresh: re-pull schedules/scores, then rebuild Elo ratings and
game predictions from the updated results.

    python scripts/refresh_weekly.py

Just chains ingest_schedules.ingest() + build_elo_ratings.main() — see those
two modules for what each step actually does. Meant to be the target of a
recurring job (a Railway Cron Job service, a plain cron entry, etc.) run
weekly during the season, ideally after Monday Night Football finishes so
every game for the week has a final score. See DEPLOYMENT.md's "Keeping Data
Fresh" section for how to wire that up.
"""
from __future__ import annotations

import asyncio

from scripts.build_elo_ratings import main as build_elo_ratings
from scripts.ingest_schedules import ingest as ingest_schedules


async def main() -> None:
    print("== Refreshing schedules/scores ==")
    await ingest_schedules(csv_path=None, from_year=1999, to_year=2100)

    print("\n== Rebuilding Elo ratings + predictions ==")
    await build_elo_ratings()


if __name__ == "__main__":
    asyncio.run(main())
