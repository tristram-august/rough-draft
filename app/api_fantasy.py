"""Fantasy scoring over the game-by-game stat table.

Points are computed in SQL so leaderboards can be sorted and paginated by the
database rather than in Python.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Float, Integer, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.db import db_session
from app.models import FantasyRank, PlayerDim, PlayerGameStat
from app.schemas import (
    FantasyBoardOut,
    FantasyBoardRow,
    FantasyGameRow,
    FantasyLeaderRow,
    FantasyLeaderboardOut,
    FantasyPlayerOut,
    FantasyPlayerSeasonOut,
    FantasyScoringPresetOut,
    FantasyStatLine,
)

router = APIRouter(tags=["fantasy"])

# Points per reception by preset — everything else is shared.
SCORING_PRESETS: dict[str, tuple[str, float]] = {
    "ppr": ("PPR", 1.0),
    "half": ("Half PPR", 0.5),
    "std": ("Standard", 0.0),
}

PASS_YARDS_PER_POINT = 25.0
RUSH_REC_YARDS_PER_POINT = 10.0
PASS_TD_POINTS = 4.0
RUSH_REC_TD_POINTS = 6.0
INTERCEPTION_POINTS = -2.0
FUMBLE_LOST_POINTS = -2.0

FLEX_POSITIONS = ("RB", "WR", "TE")

# Sort keys that map straight onto a column of the grouped subquery. "ppg" and
# "td" are computed separately in _order_expr.
SORT_COLUMNS = {
    "total": "fantasy_points",
    "games": "games",
    "name": "display_name",
    "pass_yards": "pass_yards",
    "pass_tds": "pass_tds",
    "pass_ints": "pass_ints",
    "rush_yards": "rush_yards",
    "rush_tds": "rush_tds",
    "receptions": "receptions",
    "rec_yards": "rec_yards",
    "rec_tds": "rec_tds",
}
VALID_SORTS = set(SORT_COLUMNS) | {"ppg", "td"}


def _z(col: Any) -> ColumnElement[Any]:
    """Treat missing stats as zero — most rows only fill their own position's columns."""
    return func.coalesce(col, 0)


def _points_expr(reception_points: float) -> ColumnElement[float]:
    g = PlayerGameStat
    return cast(
        _z(g.pass_yards) / PASS_YARDS_PER_POINT
        + _z(g.pass_tds) * PASS_TD_POINTS
        + _z(g.pass_ints) * INTERCEPTION_POINTS
        + _z(g.rush_yards) / RUSH_REC_YARDS_PER_POINT
        + _z(g.rush_tds) * RUSH_REC_TD_POINTS
        + _z(g.rec_yards) / RUSH_REC_YARDS_PER_POINT
        + _z(g.rec_tds) * RUSH_REC_TD_POINTS
        + _z(g.receptions) * reception_points
        + _z(g.fumbles_lost) * FUMBLE_LOST_POINTS,
        Float,
    )


def _reception_points(scoring: str) -> float:
    if scoring not in SCORING_PRESETS:
        raise HTTPException(status_code=400, detail="Unknown scoring preset")
    return SCORING_PRESETS[scoring][1]


def _stat_line(row: Any) -> FantasyStatLine:
    return FantasyStatLine(
        pass_yards=int(row.pass_yards or 0),
        pass_tds=int(row.pass_tds or 0),
        pass_ints=int(row.pass_ints or 0),
        rush_yards=int(row.rush_yards or 0),
        rush_tds=int(row.rush_tds or 0),
        receptions=int(row.receptions or 0),
        rec_yards=int(row.rec_yards or 0),
        rec_tds=int(row.rec_tds or 0),
        fumbles_lost=int(row.fumbles_lost or 0),
    )


def _sum_stat_columns() -> list[Any]:
    g = PlayerGameStat
    return [
        cast(func.sum(_z(g.pass_yards)), Integer).label("pass_yards"),
        cast(func.sum(_z(g.pass_tds)), Integer).label("pass_tds"),
        cast(func.sum(_z(g.pass_ints)), Integer).label("pass_ints"),
        cast(func.sum(_z(g.rush_yards)), Integer).label("rush_yards"),
        cast(func.sum(_z(g.rush_tds)), Integer).label("rush_tds"),
        cast(func.sum(_z(g.receptions)), Integer).label("receptions"),
        cast(func.sum(_z(g.rec_yards)), Integer).label("rec_yards"),
        cast(func.sum(_z(g.rec_tds)), Integer).label("rec_tds"),
        cast(func.sum(_z(g.fumbles_lost)), Integer).label("fumbles_lost"),
    ]


@router.get("/fantasy/board/seasons", response_model=list[int])
async def fantasy_board_seasons(session: AsyncSession = Depends(db_session)) -> list[int]:
    """Seasons that have a preseason draft board loaded."""
    stmt = select(FantasyRank.season).distinct().order_by(FantasyRank.season.desc())
    return [int(s) for s in (await session.execute(stmt)).scalars().all()]


@router.get("/fantasy/board", response_model=FantasyBoardOut)
async def fantasy_board(
    season: int = Query(...),
    position: str = Query(default="ALL"),
    limit: int = Query(default=300, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(db_session),
) -> FantasyBoardOut:
    position = position.upper()

    filters = [FantasyRank.season == season]
    if position == "FLEX":
        filters.append(FantasyRank.position.in_(FLEX_POSITIONS))
    elif position != "ALL":
        filters.append(FantasyRank.position == position)

    total = (
        await session.execute(select(func.count()).select_from(FantasyRank).where(*filters))
    ).scalar_one()

    rows = (
        await session.execute(
            select(FantasyRank)
            .where(*filters)
            .order_by(FantasyRank.overall_rank)
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()

    # Positions actually present this season, ordered the way a board reads.
    present = set(
        (
            await session.execute(
                select(FantasyRank.position).distinct().where(FantasyRank.season == season)
            )
        ).scalars().all()
    )
    ordered = [p for p in ("QB", "RB", "WR", "TE", "K", "DST") if p in present]
    ordered += sorted(present - set(ordered))

    return FantasyBoardOut(
        season=season,
        total=total,
        positions=ordered,
        rows=[
            FantasyBoardRow(
                overall_rank=r.overall_rank,
                tier=r.tier,
                player_name=r.player_name,
                team=r.team,
                position=r.position,
                position_rank=r.position_rank,
                bye_week=r.bye_week,
                sos=r.sos,
                ecr_vs_adp=r.ecr_vs_adp,
                avg_diff=r.avg_diff,
                gsis_id=r.gsis_id,
            )
            for r in rows
        ],
    )


@router.get("/fantasy/scoring", response_model=list[FantasyScoringPresetOut])
async def scoring_presets() -> list[FantasyScoringPresetOut]:
    return [
        FantasyScoringPresetOut(key=key, label=label, points_per_reception=ppr)  # type: ignore[arg-type]
        for key, (label, ppr) in SCORING_PRESETS.items()
    ]


@router.get("/fantasy/seasons", response_model=list[int])
async def fantasy_seasons(session: AsyncSession = Depends(db_session)) -> list[int]:
    stmt = select(PlayerGameStat.season).distinct().order_by(PlayerGameStat.season.desc())
    return [int(s) for s in (await session.execute(stmt)).scalars().all()]


@router.get("/fantasy/weeks", response_model=list[int])
async def fantasy_weeks(
    season: int = Query(...),
    season_type: str = Query(default="REG", max_length=8),
    session: AsyncSession = Depends(db_session),
) -> list[int]:
    stmt = (
        select(PlayerGameStat.week)
        .distinct()
        .where(
            PlayerGameStat.season == season,
            PlayerGameStat.season_type == season_type,
            PlayerGameStat.week.is_not(None),
        )
        .order_by(PlayerGameStat.week)
    )
    return [int(w) for w in (await session.execute(stmt)).scalars().all()]


@router.get("/fantasy/leaderboard", response_model=FantasyLeaderboardOut)
async def fantasy_leaderboard(
    season: int = Query(...),
    week: int | None = Query(default=None, ge=1, le=30),
    season_type: str = Query(default="REG", max_length=8),
    position: str = Query(default="ALL"),
    scoring: str = Query(default="ppr"),
    sort: str = Query(default="total"),
    direction: str = Query(default="desc"),
    min_games: int = Query(default=1, ge=1, le=17),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(db_session),
) -> FantasyLeaderboardOut:
    if position not in ("ALL", "QB", "RB", "WR", "TE", "FLEX"):
        raise HTTPException(status_code=400, detail="Unknown position filter")
    if sort not in VALID_SORTS:
        raise HTTPException(status_code=400, detail="Unknown sort")
    if direction not in ("asc", "desc"):
        raise HTTPException(status_code=400, detail="Unknown sort direction")

    reception_points = _reception_points(scoring)
    g = PlayerGameStat
    points = _points_expr(reception_points)

    filters: list[Any] = [g.season == season, g.season_type == season_type]
    if week is not None:
        filters.append(g.week == week)

    if position == "FLEX":
        filters.append(PlayerDim.position.in_(FLEX_POSITIONS))
    elif position != "ALL":
        filters.append(PlayerDim.position == position)

    games_expr = func.count(func.distinct(g.game_id)).label("games")
    total_points = func.sum(points).label("fantasy_points")
    # mode() picks the team the player appeared for most often in the window.
    team_expr = func.mode().within_group(g.team).label("team")

    grouped = (
        select(
            g.player_gsis_id.label("gsis_id"),
            func.max(PlayerDim.display_name).label("display_name"),
            func.max(PlayerDim.position).label("position"),
            func.max(PlayerDim.headshot).label("headshot"),
            team_expr,
            games_expr,
            total_points,
            *_sum_stat_columns(),
        )
        .join(PlayerDim, PlayerDim.gsis_id == g.player_gsis_id, isouter=(position == "ALL"))
        .where(*filters)
        .group_by(g.player_gsis_id)
    )
    if min_games > 1:
        grouped = grouped.having(games_expr >= min_games)

    sub = grouped.subquery()
    ppg = (sub.c.fantasy_points / func.nullif(sub.c.games, 0)).label("points_per_game")

    if sort == "ppg":
        order_col = ppg
    elif sort == "td":
        order_col = sub.c.pass_tds + sub.c.rush_tds + sub.c.rec_tds
    else:
        order_col = sub.c[SORT_COLUMNS[sort]]

    ordering = order_col.asc() if direction == "asc" else order_col.desc()

    total = (await session.execute(select(func.count()).select_from(sub))).scalar_one()

    stmt = (
        select(sub, ppg)
        # gsis_id breaks ties so paging stays stable across requests.
        .order_by(ordering.nulls_last(), sub.c.gsis_id)
        .limit(limit)
        .offset(offset)
    )
    rows = (await session.execute(stmt)).all()

    leaders = [
        FantasyLeaderRow(
            rank=offset + i + 1,
            gsis_id=row.gsis_id,
            name=row.display_name or row.gsis_id,
            position=row.position,
            team=row.team,
            headshot=row.headshot,
            games=int(row.games or 0),
            fantasy_points=round(float(row.fantasy_points or 0.0), 1),
            points_per_game=round(float(row.points_per_game or 0.0), 1),
            stats=_stat_line(row),
        )
        for i, row in enumerate(rows)
    ]

    return FantasyLeaderboardOut(
        season=season,
        week=week,
        season_type=season_type,
        scoring=scoring,  # type: ignore[arg-type]
        position=position,  # type: ignore[arg-type]
        sort=sort,  # type: ignore[arg-type]
        direction=direction,  # type: ignore[arg-type]
        total=total,
        rows=leaders,
    )


@router.get("/fantasy/player/{gsis_id}", response_model=FantasyPlayerOut)
async def fantasy_player(
    gsis_id: str,
    scoring: str = Query(default="ppr"),
    season: int | None = Query(default=None),
    season_type: str = Query(default="REG", max_length=8),
    session: AsyncSession = Depends(db_session),
) -> FantasyPlayerOut:
    reception_points = _reception_points(scoring)
    g = PlayerGameStat
    points = _points_expr(reception_points)

    dim = (
        await session.execute(select(PlayerDim).where(PlayerDim.gsis_id == gsis_id))
    ).scalars().first()

    # Season-by-season rollup, newest first.
    season_stmt = (
        select(
            g.season.label("season"),
            func.mode().within_group(g.team).label("team"),
            func.count(func.distinct(g.game_id)).label("games"),
            func.sum(points).label("fantasy_points"),
            *_sum_stat_columns(),
        )
        .where(g.player_gsis_id == gsis_id, g.season_type == season_type)
        .group_by(g.season)
        .order_by(g.season.desc())
    )
    season_rows = (await session.execute(season_stmt)).all()
    if not season_rows and dim is None:
        raise HTTPException(status_code=404, detail="Player not found")

    seasons = [
        FantasyPlayerSeasonOut(
            season=int(row.season),
            team=row.team,
            games=int(row.games or 0),
            fantasy_points=round(float(row.fantasy_points or 0.0), 1),
            points_per_game=round(float(row.fantasy_points or 0.0) / (row.games or 1), 1),
            stats=_stat_line(row),
        )
        for row in season_rows
    ]

    # Game log for one season — defaults to the most recent with data.
    target_season = season if season is not None else (seasons[0].season if seasons else None)
    games: list[FantasyGameRow] = []
    if target_season is not None:
        game_stmt = (
            select(
                g.season,
                g.week,
                g.season_type,
                g.team,
                g.opponent_team,
                points.label("fantasy_points"),
                g.pass_yards,
                g.pass_tds,
                g.pass_ints,
                g.rush_yards,
                g.rush_tds,
                g.receptions,
                g.rec_yards,
                g.rec_tds,
                g.fumbles_lost,
            )
            .where(
                g.player_gsis_id == gsis_id,
                g.season == target_season,
                g.season_type == season_type,
            )
            .order_by(g.week)
        )
        games = [
            FantasyGameRow(
                season=int(row.season),
                week=int(row.week) if row.week is not None else None,
                season_type=row.season_type,
                team=row.team,
                opponent=row.opponent_team,
                fantasy_points=round(float(row.fantasy_points or 0.0), 1),
                stats=_stat_line(row),
            )
            for row in (await session.execute(game_stmt)).all()
        ]

    return FantasyPlayerOut(
        gsis_id=gsis_id,
        name=(dim.display_name if dim and dim.display_name else gsis_id),
        position=dim.position if dim else None,
        headshot=dim.headshot if dim else None,
        scoring=scoring,  # type: ignore[arg-type]
        seasons=seasons,
        games=games,
    )
