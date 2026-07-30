"""Schedule endpoints backed by the nflverse `game` table."""
from __future__ import annotations

from datetime import date, datetime, time

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import db_session
from app.models import Game, Team
from app.schemas import GameOut, UpcomingScheduleOut

router = APIRouter(tags=["schedule"])

# A slate is "current" for a while after kickoff so the panel doesn't jump to
# next week the moment Sunday's early games start.
IN_SEASON_WINDOW_DAYS = 3


async def _team_names(session: AsyncSession) -> dict[str, str]:
    rows = (await session.execute(select(Team.abbrev, Team.name))).all()
    return {abbrev: name for abbrev, name in rows}


def _kickoff(game: Game) -> datetime | None:
    if game.gameday is None:
        return None
    if not game.gametime:
        return datetime.combine(game.gameday, time(0, 0))
    try:
        hh, mm = game.gametime.split(":")[:2]
        return datetime.combine(game.gameday, time(int(hh), int(mm)))
    except (ValueError, TypeError):
        return datetime.combine(game.gameday, time(0, 0))


def _to_out(game: Game, names: dict[str, str]) -> GameOut:
    return GameOut(
        game_id=game.game_id,
        season=game.season,
        game_type=game.game_type,
        week=game.week,
        gameday=game.gameday,
        weekday=game.weekday,
        gametime=game.gametime,
        kickoff_et=_kickoff(game),
        away_team=game.away_team,
        home_team=game.home_team,
        away_name=names.get(game.away_team),
        home_name=names.get(game.home_team),
        away_score=game.away_score,
        home_score=game.home_score,
        final=game.away_score is not None and game.home_score is not None,
        spread_line=game.spread_line,
        total_line=game.total_line,
        div_game=game.div_game,
        stadium=game.stadium,
    )


@router.get("/schedule/upcoming", response_model=UpcomingScheduleOut)
async def upcoming_schedule(
    limit: int = Query(default=16, ge=1, le=32),
    session: AsyncSession = Depends(db_session),
) -> UpcomingScheduleOut:
    """
    The next slate of games. In-season this is the current/next week; in the
    offseason it's Week 1 with a countdown.
    """
    today = date.today()

    # Find the season/week of the next game that hasn't finished yet, treating
    # the last few days as still current.
    cutoff = date.fromordinal(today.toordinal() - IN_SEASON_WINDOW_DAYS)
    next_game_stmt = (
        select(Game.season, Game.week, Game.game_type)
        .where(Game.gameday.is_not(None), Game.gameday >= cutoff)
        .order_by(Game.gameday, Game.game_id)
        .limit(1)
    )
    row = (await session.execute(next_game_stmt)).first()

    if row is None:
        return UpcomingScheduleOut(games=[], in_season=False)

    season, week, game_type = row

    games_stmt = (
        select(Game)
        .where(Game.season == season, Game.week == week)
        .order_by(Game.gameday, Game.gametime, Game.game_id)
        .limit(limit)
    )
    games = (await session.execute(games_stmt)).scalars().all()
    names = await _team_names(session)

    kickoffs = [k for k in (_kickoff(g) for g in games) if k is not None]
    first_kickoff = min(kickoffs) if kickoffs else None
    days_until = (first_kickoff.date() - today).days if first_kickoff else None

    return UpcomingScheduleOut(
        season=season,
        week=week,
        game_type=game_type,
        days_until_kickoff=days_until,
        first_kickoff_et=first_kickoff,
        in_season=days_until is not None and days_until <= 7,
        games=[_to_out(g, names) for g in games],
    )


@router.get("/schedule/week", response_model=list[GameOut])
async def schedule_week(
    season: int = Query(...),
    week: int = Query(..., ge=1, le=25),
    session: AsyncSession = Depends(db_session),
) -> list[GameOut]:
    stmt = (
        select(Game)
        .where(Game.season == season, Game.week == week)
        .order_by(Game.gameday, Game.gametime, Game.game_id)
    )
    games = (await session.execute(stmt)).scalars().all()
    names = await _team_names(session)
    return [_to_out(g, names) for g in games]


@router.get("/schedule/seasons", response_model=list[int])
async def schedule_seasons(session: AsyncSession = Depends(db_session)) -> list[int]:
    stmt = select(Game.season).distinct().order_by(Game.season.desc())
    return [int(s) for s in (await session.execute(stmt)).scalars().all()]
