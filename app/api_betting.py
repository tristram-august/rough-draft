"""Player prop probability endpoints for the Betting tab (prototype)."""
from __future__ import annotations

import asyncio
import time

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

import functools

from app.betting.engine import STATS, PredictionContext, ReceiverGame, backtest, prob_for_stat
from app.betting.passing import PASSER_STATS, GameLevelContext, PasserGame
from app.betting.rushing import RUSHER_STATS, RusherGame
from app.db import db_session
from app.models import Game, PlayerDim, PlayerGameStat

router = APIRouter(prefix="/betting", tags=["betting"])

FIRST_SEASON = 2016
CACHE_SECONDS = 600
THIN_SAMPLE_GAMES = 4
GAME_LOG_SIZE = 8
DISCLAIMER = "Prototype model. Not calibrated for live betting decisions."

GAME_LEVEL_SPECS = {**PASSER_STATS, **RUSHER_STATS}
SPECS = {**STATS, **GAME_LEVEL_SPECS}
GROUP_OF = {
    **{k: "receiving" for k in STATS},
    **{k: "passing" for k in PASSER_STATS},
    **{k: "rushing" for k in RUSHER_STATS},
}
GAME_LEVEL_CONTEXT = functools.partial(GameLevelContext, specs=GAME_LEVEL_SPECS)

_cache: dict = {}
_calibration_cache: dict = {}


class CalibrationBucket(BaseModel):
    predicted: float
    actual: float
    n: int


class CalibrationOut(BaseModel):
    stat: str
    first_season: int
    last_season: int
    predictions: int
    brier_model: float | None
    brier_baseline: float | None
    buckets: list[CalibrationBucket]


class PlayerOut(BaseModel):
    gsis_id: str
    name: str
    team: str | None
    position: str | None


class DistributionPoint(BaseModel):
    threshold: int
    p_over: float


class GameLogRow(BaseModel):
    season: int
    week: int
    opponent: str
    values: dict[str, float]


class TopAllowedGame(BaseModel):
    player: str
    season: int
    week: int
    value: float


class OpponentAllowed(BaseModel):
    team: str
    stat: str
    games: int
    avg_season: float | None
    avg_last4: float | None
    league_avg: float | None
    top_games: list[TopAllowedGame]


class PlayerUsage(BaseModel):
    target_share_season: float | None
    target_share_last4: float | None
    carry_share_season: float | None
    carry_share_last4: float | None
    air_yards_share_season: float | None
    air_yards_share_last4: float | None
    volume_per_game_season: float | None
    volume_per_game_last4: float | None


class GameEnvironment(BaseModel):
    total_line: float | None
    spread_line: float | None
    implied_team_total: float | None
    roof: str | None


class PropContext(BaseModel):
    opponent: OpponentAllowed
    usage: PlayerUsage
    game: GameEnvironment


class PlayerPropOut(BaseModel):
    gsis_id: str
    name: str
    position: str | None
    team: str
    season: int
    week: int
    opponent: str
    stat: str
    group: str
    line_max: int
    mean: float
    games_used: int
    thin_sample: bool
    distribution: list[DistributionPoint]
    game_log: list[GameLogRow]
    context: PropContext
    disclaimer: str


class UpcomingWeekOut(BaseModel):
    season: int
    week: int | None


def _avg(values: list[float], digits: int = 1) -> float | None:
    return round(sum(values) / len(values), digits) if values else None


def _validate_stat(stat: str) -> str:
    if stat not in SPECS:
        raise HTTPException(status_code=400, detail=f"Unknown stat: {stat}")
    return stat


async def _load_receiver_games(session: AsyncSession, last_season: int) -> list[ReceiverGame]:
    key = ("receiving", last_season)
    cached = _cache.get(key)
    if cached and time.monotonic() - cached[0] < CACHE_SECONDS:
        return cached[1]

    rows = (
        await session.execute(
            select(
                PlayerGameStat.player_gsis_id,
                PlayerGameStat.season,
                PlayerGameStat.week,
                PlayerGameStat.team,
                PlayerGameStat.opponent_team,
                PlayerGameStat.targets,
                PlayerGameStat.receptions,
                PlayerGameStat.rec_yards,
                PlayerGameStat.rec_tds,
            ).where(
                PlayerGameStat.season_type == "REG",
                PlayerGameStat.season >= FIRST_SEASON,
                PlayerGameStat.season <= last_season,
                PlayerGameStat.position_group.in_(["WR", "TE"]),
                PlayerGameStat.targets > 0,
            )
        )
    ).all()
    games = [
        ReceiverGame(
            season=r.season,
            week=r.week,
            player_id=r.player_gsis_id,
            team=r.team,
            opponent=r.opponent_team,
            targets=float(r.targets),
            receptions=float(r.receptions or 0),
            yards=float(r.rec_yards or 0),
            tds=float(r.rec_tds or 0),
        )
        for r in rows
    ]
    _cache[key] = (time.monotonic(), games)
    return games


async def _load_passer_games(session: AsyncSession, last_season: int) -> list[PasserGame]:
    key = ("passing", last_season)
    cached = _cache.get(key)
    if cached and time.monotonic() - cached[0] < CACHE_SECONDS:
        return cached[1]

    rows = (
        await session.execute(
            select(
                PlayerGameStat.player_gsis_id,
                PlayerGameStat.season,
                PlayerGameStat.week,
                PlayerGameStat.team,
                PlayerGameStat.opponent_team,
                PlayerGameStat.pass_attempts,
                PlayerGameStat.pass_yards,
                PlayerGameStat.pass_tds,
                PlayerGameStat.pass_ints,
            ).where(
                PlayerGameStat.season_type == "REG",
                PlayerGameStat.season >= FIRST_SEASON,
                PlayerGameStat.season <= last_season,
                PlayerGameStat.position_group == "QB",
                PlayerGameStat.pass_attempts > 0,
            )
        )
    ).all()
    games = [
        PasserGame(
            season=r.season,
            week=r.week,
            player_id=r.player_gsis_id,
            team=r.team,
            opponent=r.opponent_team,
            attempts=float(r.pass_attempts),
            pass_yards=float(r.pass_yards or 0),
            pass_tds=float(r.pass_tds or 0),
            ints=float(r.pass_ints or 0),
        )
        for r in rows
    ]
    _cache[key] = (time.monotonic(), games)
    return games


async def _load_rusher_games(session: AsyncSession, last_season: int) -> list[RusherGame]:
    key = ("rushing", last_season)
    cached = _cache.get(key)
    if cached and time.monotonic() - cached[0] < CACHE_SECONDS:
        return cached[1]

    rows = (
        await session.execute(
            select(
                PlayerGameStat.player_gsis_id,
                PlayerGameStat.season,
                PlayerGameStat.week,
                PlayerGameStat.team,
                PlayerGameStat.opponent_team,
                PlayerGameStat.rush_attempts,
                PlayerGameStat.rush_yards,
                PlayerGameStat.rush_tds,
            ).where(
                PlayerGameStat.season_type == "REG",
                PlayerGameStat.season >= FIRST_SEASON,
                PlayerGameStat.season <= last_season,
                PlayerGameStat.position_group == "RB",
                PlayerGameStat.rush_attempts > 0,
            )
        )
    ).all()
    games = [
        RusherGame(
            season=r.season,
            week=r.week,
            player_id=r.player_gsis_id,
            team=r.team,
            opponent=r.opponent_team,
            attempts=float(r.rush_attempts),
            yards=float(r.rush_yards or 0),
            tds=float(r.rush_tds or 0),
        )
        for r in rows
    ]
    _cache[key] = (time.monotonic(), games)
    return games


async def _games_for(session: AsyncSession, season: int, group: str) -> list:
    if group == "passing":
        return await _load_passer_games(session, season)
    if group == "rushing":
        return await _load_rusher_games(session, season)
    return await _load_receiver_games(session, season)


def _context_for(games: list, season: int, week: int, stat: str):
    if GROUP_OF[stat] in ("passing", "rushing"):
        return GAME_LEVEL_CONTEXT(games, season, week, stat=stat)
    return PredictionContext(games, season, week, stat=stat)


def _game_values(g, group: str) -> dict[str, float]:
    if group == "passing":
        return {"attempts": g.attempts, "pass_yards": g.pass_yards, "pass_tds": g.pass_tds, "ints": g.ints}
    if group == "rushing":
        return {"attempts": g.attempts, "rush_yards": g.yards, "rush_tds": g.tds}
    return {"targets": g.targets, "receptions": g.receptions, "yards": g.yards, "tds": g.tds}


async def _roster(session: AsyncSession, games: list, season: int) -> list[PlayerOut]:
    latest_team: dict[str, str] = {}
    for g in sorted(games, key=lambda g: (g.season, g.week)):
        if g.season == season:
            latest_team[g.player_id] = g.team
    if not latest_team:
        return []

    dims = (
        await session.execute(
            select(PlayerDim.gsis_id, PlayerDim.display_name, PlayerDim.position).where(
                PlayerDim.gsis_id.in_(list(latest_team))
            )
        )
    ).all()
    out = [
        PlayerOut(
            gsis_id=d.gsis_id,
            name=d.display_name or d.gsis_id,
            team=latest_team.get(d.gsis_id),
            position=d.position,
        )
        for d in dims
    ]
    out.sort(key=lambda r: r.name)
    return out


@router.get("/upcoming-week", response_model=UpcomingWeekOut)
async def upcoming_week(
    season: int = Query(...),
    session: AsyncSession = Depends(db_session),
) -> UpcomingWeekOut:
    games = await _load_receiver_games(session, season)
    played = [g.week for g in games if g.season == season]
    return UpcomingWeekOut(season=season, week=max(played) + 1 if played else None)


@router.get("/calibration", response_model=CalibrationOut)
async def calibration(
    season: int = Query(...),
    stat: str = Query("rec_yards"),
    session: AsyncSession = Depends(db_session),
) -> CalibrationOut:
    _validate_stat(stat)
    key = (season, stat)
    now = time.monotonic()
    cached = _calibration_cache.get(key)
    if cached and now - cached[0] < CACHE_SECONDS:
        return cached[1]

    group = GROUP_OF[stat]
    games = await _games_for(session, season, group)
    context_cls = GAME_LEVEL_CONTEXT if group in ("passing", "rushing") else PredictionContext
    result = await asyncio.to_thread(backtest, games, season - 1, season, stat, SPECS, context_cls)
    out = CalibrationOut(**result)
    _calibration_cache[key] = (now, out)
    return out


@router.get("/receivers", response_model=list[PlayerOut])
async def list_receivers(
    season: int = Query(...),
    session: AsyncSession = Depends(db_session),
) -> list[PlayerOut]:
    games = await _load_receiver_games(session, season)
    return await _roster(session, games, season)


@router.get("/passers", response_model=list[PlayerOut])
async def list_passers(
    season: int = Query(...),
    session: AsyncSession = Depends(db_session),
) -> list[PlayerOut]:
    games = await _load_passer_games(session, season)
    return await _roster(session, games, season)


@router.get("/rushers", response_model=list[PlayerOut])
async def list_rushers(
    season: int = Query(...),
    session: AsyncSession = Depends(db_session),
) -> list[PlayerOut]:
    games = await _load_rusher_games(session, season)
    return await _roster(session, games, season)


@router.get("/receiving-prop", response_model=PlayerPropOut)
async def player_prop(
    gsis_id: str = Query(...),
    season: int = Query(...),
    week: int = Query(..., ge=1, le=22),
    stat: str = Query("rec_yards"),
    session: AsyncSession = Depends(db_session),
) -> PlayerPropOut:
    _validate_stat(stat)
    spec = SPECS[stat]
    group = GROUP_OF[stat]
    games = await _games_for(session, season, group)
    ctx = _context_for(games, season, week, stat)
    hist = ctx.history.get(gsis_id, [])
    if len(hist) < 3:
        raise HTTPException(status_code=404, detail="Not enough prior games for this player.")

    team = hist[-1].team
    game = (
        await session.execute(
            select(Game).where(
                Game.season == season,
                Game.week == week,
                or_(Game.home_team == team, Game.away_team == team),
            )
        )
    ).scalar_one_or_none()
    if game is None:
        raise HTTPException(status_code=404, detail="No game for this player's team that week.")
    opponent = game.away_team if game.home_team == team else game.home_team

    dim = (
        await session.execute(
            select(PlayerDim.display_name, PlayerDim.position).where(PlayerDim.gsis_id == gsis_id)
        )
    ).first()

    values, weights = ctx.predict(gsis_id, opponent)

    prior_season = [g for g in games if g.season == season and g.week < week]
    opp_games = sorted((g for g in prior_season if g.opponent == opponent), key=lambda g: g.week)
    last_four_weeks = set(sorted({g.week for g in opp_games})[-4:])
    top = sorted(opp_games, key=spec.value, reverse=True)[:3]
    top_names = dict(
        (
            await session.execute(
                select(PlayerDim.gsis_id, PlayerDim.display_name).where(
                    PlayerDim.gsis_id.in_([g.player_id for g in top])
                )
            )
        ).all()
    ) if top else {}

    team_carry_rows = (
        await session.execute(
            select(PlayerGameStat.week, func.sum(PlayerGameStat.rush_attempts).label("carries"))
            .where(
                PlayerGameStat.team == team,
                PlayerGameStat.season == season,
                PlayerGameStat.season_type == "REG",
                PlayerGameStat.week < week,
            )
            .group_by(PlayerGameStat.week)
        )
    ).all()
    team_carries = {r.week: float(r.carries or 0) for r in team_carry_rows}

    player_rows = (
        await session.execute(
            select(
                PlayerGameStat.week,
                PlayerGameStat.target_share,
                PlayerGameStat.air_yards_share,
                PlayerGameStat.rush_attempts,
                PlayerGameStat.targets,
                PlayerGameStat.pass_attempts,
            )
            .where(
                PlayerGameStat.player_gsis_id == gsis_id,
                PlayerGameStat.season == season,
                PlayerGameStat.season_type == "REG",
                PlayerGameStat.week < week,
            )
            .order_by(PlayerGameStat.week)
        )
    ).all()
    ts = [r.target_share for r in player_rows if r.target_share is not None]
    ays = [r.air_yards_share for r in player_rows if r.air_yards_share is not None]
    carry_shares = [
        float(r.rush_attempts or 0) / team_carries[r.week]
        for r in player_rows
        if team_carries.get(r.week, 0) > 0
    ]
    volume_field = {"receiving": "targets", "rushing": "rush_attempts", "passing": "pass_attempts"}[group]
    volumes = [float(getattr(r, volume_field) or 0) for r in player_rows]
    usage = PlayerUsage(
        target_share_season=_avg(ts, 3),
        target_share_last4=_avg(ts[-4:], 3),
        carry_share_season=_avg(carry_shares, 3),
        carry_share_last4=_avg(carry_shares[-4:], 3),
        air_yards_share_season=_avg(ays, 3) if group == "receiving" else None,
        air_yards_share_last4=_avg(ays[-4:], 3) if group == "receiving" else None,
        volume_per_game_season=_avg(volumes, 1),
        volume_per_game_last4=_avg(volumes[-4:], 1),
    )

    total = game.total_line
    spread = game.spread_line
    implied = None
    if total is not None and spread is not None:
        implied = total / 2 + spread / 2 if game.home_team == team else total / 2 - spread / 2

    context = PropContext(
        opponent=OpponentAllowed(
            team=opponent,
            stat=stat,
            games=len(opp_games),
            avg_season=_avg([spec.value(g) for g in opp_games], 2),
            avg_last4=_avg([spec.value(g) for g in opp_games if g.week in last_four_weeks], 2),
            league_avg=_avg([spec.value(g) for g in prior_season], 2),
            top_games=[
                TopAllowedGame(
                    player=top_names.get(g.player_id) or "Unknown player",
                    season=g.season,
                    week=g.week,
                    value=spec.value(g),
                )
                for g in top
            ],
        ),
        usage=usage,
        game=GameEnvironment(
            total_line=total,
            spread_line=spread,
            implied_team_total=round(implied, 1) if implied is not None else None,
            roof=game.roof,
        ),
    )

    return PlayerPropOut(
        gsis_id=gsis_id,
        name=dim.display_name if dim and dim.display_name else gsis_id,
        position=dim.position if dim else None,
        team=team,
        season=season,
        week=week,
        opponent=opponent,
        stat=stat,
        group=group,
        line_max=spec.line_max,
        mean=round(float(np.average(values, weights=weights)), 2),
        games_used=len(hist),
        thin_sample=len(hist) < THIN_SAMPLE_GAMES,
        distribution=[
            DistributionPoint(threshold=t, p_over=round(prob_for_stat(spec, values, weights, t), 4))
            for t in range(0, spec.line_max + 1)
        ],
        game_log=[
            GameLogRow(
                season=g.season,
                week=g.week,
                opponent=g.opponent,
                values=_game_values(g, group),
            )
            for g in reversed(hist[-GAME_LOG_SIZE:])
        ],
        context=context,
        disclaimer=DISCLAIMER,
    )
