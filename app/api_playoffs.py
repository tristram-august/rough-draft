"""
Playoff odds (see app/playoffs.py and scripts/build_playoff_odds.py): each
team's chance to make the playoffs, win its division, earn the bye, and win
it all, as of a given week -- plus the model's out-of-sample backtest.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import db_session
from app.models import PlayoffCalibration, PlayoffOdds, Team
from app.schemas import (
    PlayoffCalibrationOut,
    PlayoffCalibrationRow,
    PlayoffOddsHistoryPoint,
    PlayoffOddsOut,
    PlayoffTeamOdds,
)

router = APIRouter(tags=["playoffs"])


@router.get("/playoffs/odds", response_model=PlayoffOddsOut)
async def playoff_odds(
    season: int | None = Query(default=None),
    week: int | None = Query(default=None, ge=0, le=18),
    session: AsyncSession = Depends(db_session),
) -> PlayoffOddsOut:
    if season is None:
        season = (await session.execute(select(func.max(PlayoffOdds.season)))).scalar()
        if season is None:
            raise HTTPException(status_code=404, detail="No playoff odds have been built yet")

    rows = (
        await session.execute(select(PlayoffOdds).where(PlayoffOdds.season == season).order_by(PlayoffOdds.week))
    ).scalars().all()
    if not rows:
        raise HTTPException(status_code=404, detail="No playoff odds for that season")
    weeks = sorted({r.week for r in rows})
    week = weeks[-1] if week is None else week
    if week not in weeks:
        raise HTTPException(status_code=404, detail="No playoff odds for that week")

    history: dict[str, list[PlayoffOddsHistoryPoint]] = {}
    for r in rows:
        history.setdefault(r.team, []).append(
            PlayoffOddsHistoryPoint(
                week=r.week, make_playoffs=r.make_playoffs, win_division=r.win_division, win_super_bowl=r.win_super_bowl
            )
        )

    teams = {t.abbrev: t for t in (await session.execute(select(Team))).scalars()}
    current = [r for r in rows if r.week == week]
    return PlayoffOddsOut(
        season=season,
        week=week,
        weeks=weeks,
        sims=current[0].sims,
        updated_at=max(r.updated_at for r in current),
        teams=[
            PlayoffTeamOdds(
                team=r.team,
                team_name=f"{teams[r.team].city} {teams[r.team].name}" if r.team in teams else None,
                conference=teams[r.team].conference if r.team in teams else None,
                division=teams[r.team].division if r.team in teams else None,
                elo=round(r.elo, 1),
                wins=r.wins,
                losses=r.losses,
                mean_wins=round(r.mean_wins, 2),
                make_playoffs=r.make_playoffs,
                win_division=r.win_division,
                first_seed=r.first_seed,
                win_conference=r.win_conference,
                win_super_bowl=r.win_super_bowl,
                seed_probs=json.loads(r.seed_probs),
                history=[h for h in history[r.team] if h.week <= week],
            )
            for r in sorted(current, key=lambda r: -r.make_playoffs)
        ],
    )


@router.get("/playoffs/calibration", response_model=PlayoffCalibrationOut)
async def playoff_calibration(session: AsyncSession = Depends(db_session)) -> PlayoffCalibrationOut:
    rows = (await session.execute(select(PlayoffCalibration).order_by(PlayoffCalibration.bucket_lo))).scalars().all()
    return PlayoffCalibrationOut(
        seasons=rows[0].seasons if rows else None,
        rows=[
            PlayoffCalibrationRow(bucket_lo=r.bucket_lo, bucket_hi=r.bucket_hi, n=r.n, predicted=r.predicted, actual=r.actual)
            for r in rows
        ],
    )
