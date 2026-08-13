from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import db_session
from app.models import PlayerInjury
from app.schemas import InjuryOut

router = APIRouter(tags=["injuries"])


@router.get("/injuries", response_model=list[InjuryOut])
async def list_injuries(session: AsyncSession = Depends(db_session)) -> list[InjuryOut]:
    rows = (await session.execute(select(PlayerInjury))).scalars().all()
    return [
        InjuryOut(
            gsis_id=r.gsis_id,
            player_name=r.player_name,
            team=r.team,
            position=r.position,
            status=r.status,
            status_short=r.status_short,
            injury_type=r.injury_type,
            comment=r.comment,
            probability_of_playing=r.probability_of_playing,
            updated_at=r.updated_at,
        )
        for r in rows
    ]
