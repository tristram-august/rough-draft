from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DraftPick, PickOutcome, PlayerSeasonStat


def _label(score: int) -> str:
    if score < 20:
        return "Bust"
    if score < 40:
        return "BelowAvg"
    if score < 60:
        return "Avg"
    if score < 75:
        return "Good"
    if score < 90:
        return "Hit"
    return "Elite"


async def compute_outcomes_v1(session: AsyncSession, *, year: int) -> int:
    """
    Placeholder v1 scoring:
      score ~= min(100, games*2 + starts*3) aggregated across seasons.

    Swap in better metrics later (AV/WAR/contract/pos-adjusted baselines).
    """
    picks_res = await session.execute(select(DraftPick).where(DraftPick.year == year))
    picks = list(picks_res.scalars().all())
    if not picks:
        return 0

    updated = 0
    for pick in picks:
        stats_res = await session.execute(select(PlayerSeasonStat).where(PlayerSeasonStat.player_id == pick.player_id))
        stats = stats_res.scalars().all()

        games = sum((s.games or 0) for s in stats)
        starts = sum((s.starts or 0) for s in stats)

        score = min(100, games * 2 + starts * 3)
        label = _label(score)

        existing = await session.get(PickOutcome, pick.id)
        if existing:
            existing.outcome_score = score
            existing.label = label
            existing.method_version = "v1"
        else:
            session.add(PickOutcome(pick_id=pick.id, outcome_score=score, label=label, method_version="v1"))
        updated += 1

    return updated
