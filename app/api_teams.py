"""
Team-level box score stats (see scripts/ingest_team_stats.py) -- offensive
and defensive EPA/play, yardage, and turnovers, aggregated across a season or
narrowed to one week. A team's defensive EPA/plays-faced numbers come from
its *opponent's* own row for the same game_id (that opponent's offensive
output that game is exactly what this team's defense allowed) -- see
TeamGameStat's docstring in app/models.py.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.db import db_session
from app.models import Game, Team, TeamGameStat
from app.schemas import TeamStatRow, TeamStatsOut

router = APIRouter(tags=["teams"])

SORT_COLUMNS = {
    "team": "team",
    "off_epa": "off_epa",
    "points_for": "points_for",
    "pass_yards": "pass_yards",
    "pass_tds": "pass_tds",
    "rush_yards": "rush_yards",
    "rush_tds": "rush_tds",
    "giveaways": "giveaways",
    "def_epa_allowed": "def_epa_allowed",
    "points_against": "points_against",
    "def_sacks": "def_sacks",
    "def_interceptions": "def_interceptions",
    "takeaways": "takeaways",
}
VALID_SORTS = set(SORT_COLUMNS) | {"off_epa_per_play", "def_epa_per_play_allowed", "turnover_margin"}


@router.get("/teams/seasons", response_model=list[int])
async def team_seasons(session: AsyncSession = Depends(db_session)) -> list[int]:
    stmt = select(TeamGameStat.season).distinct().order_by(TeamGameStat.season.desc())
    return [int(s) for s in (await session.execute(stmt)).scalars().all()]


@router.get("/teams/weeks", response_model=list[int])
async def team_weeks(
    season: int = Query(...),
    season_type: str = Query(default="REG", max_length=8),
    session: AsyncSession = Depends(db_session),
) -> list[int]:
    stmt = (
        select(TeamGameStat.week)
        .distinct()
        .where(
            TeamGameStat.season == season,
            TeamGameStat.season_type == season_type,
            TeamGameStat.week.is_not(None),
        )
        .order_by(TeamGameStat.week)
    )
    return [int(w) for w in (await session.execute(stmt)).scalars().all()]


@router.get("/teams/stats", response_model=TeamStatsOut)
async def team_stats(
    season: int = Query(...),
    week: int | None = Query(default=None, ge=1, le=22),
    season_type: str = Query(default="REG", max_length=8),
    sort: str = Query(default="off_epa_per_play"),
    direction: str = Query(default="desc"),
    session: AsyncSession = Depends(db_session),
) -> TeamStatsOut:
    if sort not in VALID_SORTS:
        raise HTTPException(status_code=400, detail="Unknown sort")
    if direction not in ("asc", "desc"):
        raise HTTPException(status_code=400, detail="Unknown sort direction")

    t = TeamGameStat
    opp = aliased(TeamGameStat)

    filters: list[Any] = [t.season == season, t.season_type == season_type]
    if week is not None:
        filters.append(t.week == week)

    off_plays = func.coalesce(t.attempts, 0) + func.coalesce(t.carries, 0)
    off_epa = func.coalesce(t.passing_epa, 0) + func.coalesce(t.rushing_epa, 0)
    giveaways = (
        func.coalesce(t.passing_interceptions, 0)
        + func.coalesce(t.sack_fumbles_lost, 0)
        + func.coalesce(t.rushing_fumbles_lost, 0)
        + func.coalesce(t.receiving_fumbles_lost, 0)
    )
    # def_interceptions + def_fumbles_forced is a takeaways proxy, not exact --
    # a forced fumble isn't always recovered by the forcing team.
    takeaways = func.coalesce(t.def_interceptions, 0) + func.coalesce(t.def_fumbles_forced, 0)
    opp_plays = func.coalesce(opp.attempts, 0) + func.coalesce(opp.carries, 0)
    opp_epa = func.coalesce(opp.passing_epa, 0) + func.coalesce(opp.rushing_epa, 0)

    # Final score lives on Game, not TeamGameStat -- which side is "this
    # team" depends on whether it was the home or away team that game.
    points_for = case((t.team == Game.home_team, Game.home_score), else_=Game.away_score)
    points_against = case((t.team == Game.home_team, Game.away_score), else_=Game.home_score)

    grouped = (
        select(
            t.team.label("team"),
            func.count(func.distinct(t.game_id)).label("games"),
            func.sum(off_plays).label("off_plays"),
            func.sum(off_epa).label("off_epa"),
            func.sum(func.coalesce(points_for, 0)).label("points_for"),
            func.sum(func.coalesce(t.passing_yards, 0)).label("pass_yards"),
            func.sum(func.coalesce(t.passing_tds, 0)).label("pass_tds"),
            func.sum(func.coalesce(t.rushing_yards, 0)).label("rush_yards"),
            func.sum(func.coalesce(t.rushing_tds, 0)).label("rush_tds"),
            func.sum(giveaways).label("giveaways"),
            func.sum(func.coalesce(t.def_sacks, 0)).label("def_sacks"),
            func.sum(func.coalesce(t.def_interceptions, 0)).label("def_interceptions"),
            func.sum(takeaways).label("takeaways"),
            func.sum(opp_plays).label("def_plays_faced"),
            func.sum(opp_epa).label("def_epa_allowed"),
            func.sum(func.coalesce(points_against, 0)).label("points_against"),
        )
        .outerjoin(opp, (opp.game_id == t.game_id) & (opp.team == t.opponent_team))
        .outerjoin(Game, Game.game_id == t.game_id)
        .where(*filters)
        .group_by(t.team)
    )
    sub = grouped.subquery()

    off_epa_per_play = (sub.c.off_epa / func.nullif(sub.c.off_plays, 0)).label("off_epa_per_play")
    def_epa_per_play_allowed = (sub.c.def_epa_allowed / func.nullif(sub.c.def_plays_faced, 0)).label(
        "def_epa_per_play_allowed"
    )
    turnover_margin = (sub.c.takeaways - sub.c.giveaways).label("turnover_margin")

    if sort == "off_epa_per_play":
        order_col = off_epa_per_play
    elif sort == "def_epa_per_play_allowed":
        order_col = def_epa_per_play_allowed
    elif sort == "turnover_margin":
        order_col = turnover_margin
    else:
        order_col = sub.c[SORT_COLUMNS[sort]]
    ordering = order_col.asc() if direction == "asc" else order_col.desc()

    stmt = select(sub, off_epa_per_play, def_epa_per_play_allowed, turnover_margin).order_by(
        ordering.nulls_last(), sub.c.team
    )
    rows = (await session.execute(stmt)).all()

    team_names = {
        r.abbrev: f"{r.city} {r.name}" for r in (await session.execute(select(Team.abbrev, Team.name, Team.city))).all()
    }

    return TeamStatsOut(
        season=season,
        week=week,
        season_type=season_type,
        total=len(rows),
        rows=[
            TeamStatRow(
                team=r.team,
                team_name=team_names.get(r.team),
                games=int(r.games),
                off_plays=int(r.off_plays or 0),
                off_epa=round(float(r.off_epa or 0), 1),
                off_epa_per_play=round(float(r.off_epa_per_play), 3) if r.off_epa_per_play is not None else None,
                points_for=int(r.points_for or 0),
                pass_yards=int(r.pass_yards or 0),
                pass_tds=int(r.pass_tds or 0),
                rush_yards=int(r.rush_yards or 0),
                rush_tds=int(r.rush_tds or 0),
                giveaways=int(r.giveaways or 0),
                def_plays_faced=int(r.def_plays_faced or 0),
                def_epa_allowed=round(float(r.def_epa_allowed or 0), 1),
                def_epa_per_play_allowed=(
                    round(float(r.def_epa_per_play_allowed), 3) if r.def_epa_per_play_allowed is not None else None
                ),
                def_sacks=round(float(r.def_sacks or 0), 1),
                def_interceptions=int(r.def_interceptions or 0),
                takeaways=int(r.takeaways or 0),
                points_against=int(r.points_against or 0),
                turnover_margin=int(r.turnover_margin or 0),
            )
            for r in rows
        ],
    )
