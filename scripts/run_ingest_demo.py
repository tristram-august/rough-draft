import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_sessionmaker
from app.services.ingest import DraftPickIn, ingest_draft_year
from app.services.outcomes import compute_outcomes_v1


async def main() -> None:
    session_maker = get_sessionmaker()
    async with session_maker() as session:  # type: AsyncSession
        demo_picks = [
            DraftPickIn(
                year=2016,
                round=1,
                pick_in_round=1,
                overall=1,
                team_abbrev="LAR",
                team_city="Los Angeles",
                team_name="Rams",
                player_name="Jared Goff",
                position="QB",
                college="California",
            ),
            DraftPickIn(
                year=2016,
                round=1,
                pick_in_round=2,
                overall=2,
                team_abbrev="PHI",
                team_city="Philadelphia",
                team_name="Eagles",
                player_name="Carson Wentz",
                position="QB",
                college="North Dakota State",
            ),
        ]

        await ingest_draft_year(session, year=2016, picks=demo_picks)
        await session.commit()

        await compute_outcomes_v1(session, year=2016)
        await session.commit()

    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
