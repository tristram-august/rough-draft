from __future__ import annotations

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DraftPick, PickVote

def _label_from_score(score: int, total: int) -> str:
    if total < 10:
        return "LowSignal"
    if score < 35:
        return "Bust"
    if score < 55:
        return "Debatable"
    if score < 75:
        return "Success"
    return "HomeRun"

async def get_pick_id(session: AsyncSession, *, year: int, overall: int) -> int | None:
    stmt = select(DraftPick.id).where(DraftPick.year == year, DraftPick.overall == overall)
    res = await session.execute(stmt)
    return res.scalar_one_or_none()

async def upsert_vote(
    session: AsyncSession,
    *,
    pick_id: int,
    voter_type: str,
    voter_key: str,
    value: str,
) -> PickVote:
    stmt = select(PickVote).where(
        PickVote.pick_id == pick_id,
        PickVote.voter_type == voter_type,
        PickVote.voter_key == voter_key,
    )
    res = await session.execute(stmt)
    existing = res.scalars().first()
    if existing:
        existing.value = value
        return existing

    vote = PickVote(
        pick_id=pick_id,
        voter_type=voter_type,
        voter_key=voter_key,
        value=value,
    )
    session.add(vote)
    await session.flush()
    return vote

async def get_community_votes(session: AsyncSession, *, pick_id: int) -> tuple[int, int]:
    stmt = select(
        func.sum(case((PickVote.value == "success", 1), else_=0)).label("success"),
        func.sum(case((PickVote.value == "bust", 1), else_=0)).label("bust"),
    ).where(PickVote.pick_id == pick_id)
    res = await session.execute(stmt)
    row = res.one()
    success = int(row.success or 0)
    bust = int(row.bust or 0)
    return success, bust

async def get_your_vote(session: AsyncSession, *, pick_id: int, voter_type: str, voter_key: str) -> str | None:
    stmt = select(PickVote.value).where(
        PickVote.pick_id == pick_id,
        PickVote.voter_type == voter_type,
        PickVote.voter_key == voter_key,
    )
    res = await session.execute(stmt)
    return res.scalar_one_or_none()

def community_votes_out(success: int, bust: int):
    total = success + bust
    score = int(round((success / total) * 100)) if total else 0
    return {
        "success": success,
        "bust": bust,
        "total": total,
        "community_score": score,
        "community_label": _label_from_score(score, total),
    }
