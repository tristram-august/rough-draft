"""Team-comparison stat sheets for a game (see scripts/ingest_matchup_stats.py)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import db_session
from app.models import MatchupStat
from app.schemas import MatchupStatCategoryOut, MatchupStatRowOut, MatchupStatsOut

router = APIRouter(tags=["matchup-stats"])

# Reading order; anything unexpected (a new category the scraper adds later)
# is appended after these rather than dropped.
CATEGORY_ORDER = ["Overall", "Passing", "Rushing", "Kicking", "Penalties", "Turnovers"]


def _favored(team_rank: int | None, opp_rank: int | None) -> bool | None:
    """
    Lower rank always means better-in-the-league for that specific stat,
    whether it's an offensive or defensive metric — the source data already
    normalizes direction into the rank, so there's no per-stat "higher/lower
    is better" table to get backwards here.
    """
    if team_rank is None or opp_rank is None or team_rank == opp_rank:
        return None
    return team_rank < opp_rank


@router.get("/matchup-stats/{game_id}", response_model=MatchupStatsOut)
async def matchup_stats(game_id: str, session: AsyncSession = Depends(db_session)) -> MatchupStatsOut:
    rows = (
        await session.execute(
            select(MatchupStat)
            .where(MatchupStat.game_id == game_id)
            .order_by(MatchupStat.category, MatchupStat.id)
        )
    ).scalars().all()

    by_category: dict[str, list[MatchupStatRowOut]] = {}
    source_season: int | None = None
    for r in rows:
        source_season = r.source_season
        by_category.setdefault(r.category, []).append(
            MatchupStatRowOut(
                stat_label=r.stat_label,
                team=r.team,
                team_value=r.team_value,
                team_rank=r.team_rank,
                opp_team=r.opp_team,
                opp_stat_label=r.opp_stat_label,
                opp_value=r.opp_value,
                opp_rank=r.opp_rank,
                team_favored=_favored(r.team_rank, r.opp_rank),
            )
        )

    ordered = [c for c in CATEGORY_ORDER if c in by_category]
    ordered += sorted(set(by_category) - set(CATEGORY_ORDER))

    return MatchupStatsOut(
        game_id=game_id,
        source_season=source_season,
        categories=[MatchupStatCategoryOut(category=c, rows=by_category[c]) for c in ordered],
    )
