from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PickVote


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


def _community_votes_out(success: int, bust: int) -> dict:
    total = success + bust
    score = int(round((success / total) * 100)) if total else 0
    return {
        "success": success,
        "bust": bust,
        "total": total,
        "community_score": score,
        "community_label": _label_from_score(score, total),
    }


async def get_community_votes_for_picks(
    session: AsyncSession,
    *,
    pick_ids: Iterable[int],
) -> dict[int, dict]:
    pick_ids = list(pick_ids)
    if not pick_ids:
        return {}

    stmt = (
        select(
            PickVote.pick_id.label("pick_id"),
            func.sum(case((PickVote.value == "success", 1), else_=0)).label("success"),
            func.sum(case((PickVote.value == "bust", 1), else_=0)).label("bust"),
        )
        .where(PickVote.pick_id.in_(pick_ids))
        .group_by(PickVote.pick_id)
    )
    res = await session.execute(stmt)

    out: dict[int, dict] = {}
    for row in res:
        pick_id = int(row.pick_id)
        success = int(row.success or 0)
        bust = int(row.bust or 0)
        out[pick_id] = _community_votes_out(success, bust)
    return out


async def get_your_votes_for_picks(
    session: AsyncSession,
    *,
    pick_ids: Iterable[int],
    voter_type: str,
    voter_key: str,
) -> dict[int, str]:
    pick_ids = list(pick_ids)
    if not pick_ids:
        return {}

    stmt = select(PickVote.pick_id, PickVote.value).where(
        PickVote.pick_id.in_(pick_ids),
        PickVote.voter_type == voter_type,
        PickVote.voter_key == voter_key,
    )
    res = await session.execute(stmt)
    return {int(pid): str(val) for pid, val in res.all()}