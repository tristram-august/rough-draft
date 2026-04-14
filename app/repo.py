from __future__ import annotations

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, joinedload

from app.models import DraftPick, PickOutcome, Player, PlayerSeasonStat, Team


def _apply_draft_filters(
    stmt: Select,
    *,
    year: int,
    round: int | None,
    team: str | None,
    pos: str | None,
    q: str | None,
) -> Select:
    conditions = [DraftPick.year == year]
    if round is not None:
        conditions.append(DraftPick.round == round)
    if team:
        conditions.append(func.lower(Team.abbrev) == team.lower())
    if pos:
        conditions.append(func.lower(Player.position) == pos.lower())
    if q:
        like = f"%{q.lower()}%"
        conditions.append(
            or_(
                func.lower(Player.full_name).like(like),
                func.lower(Player.college).like(like),
                func.lower(Team.abbrev).like(like),
                func.lower(Team.name).like(like),
            )
        )
    return stmt.where(and_(*conditions))


async def list_draft_board(
    session: AsyncSession,
    *,
    year: int,
    round: int | None,
    team: str | None,
    pos: str | None,
    q: str | None,
    limit: int,
    offset: int,
) -> list[DraftPick]:
    traded_team = aliased(Team)

    stmt = (
        select(DraftPick)
        .join(DraftPick.team)
        .join(DraftPick.player)
        .outerjoin(traded_team, DraftPick.traded_from_team_id == traded_team.id)
        .options(joinedload(DraftPick.team), joinedload(DraftPick.player), joinedload(DraftPick.outcome))
        .order_by(DraftPick.overall.asc())
        .limit(limit)
        .offset(offset)
    )
    stmt = _apply_draft_filters(stmt, year=year, round=round, team=team, pos=pos, q=q)

    res = await session.execute(stmt)
    return list(res.scalars().unique().all())


async def get_pick_detail(session: AsyncSession, *, year: int, overall: int) -> DraftPick | None:
    stmt = (
        select(DraftPick)
        .where(DraftPick.year == year, DraftPick.overall == overall)
        .options(joinedload(DraftPick.team), joinedload(DraftPick.player), joinedload(DraftPick.outcome))
    )
    res = await session.execute(stmt)
    return res.scalars().first()


async def get_player_detail(session: AsyncSession, *, player_id: int) -> tuple[Player | None, list[DraftPick], list[PlayerSeasonStat]]:
    player_stmt = select(Player).where(Player.id == player_id)
    p_res = await session.execute(player_stmt)
    player = p_res.scalars().first()
    if player is None:
        return None, [], []

    picks_stmt = (
        select(DraftPick)
        .where(DraftPick.player_id == player_id)
        .options(joinedload(DraftPick.team), joinedload(DraftPick.player), joinedload(DraftPick.outcome))
        .order_by(DraftPick.year.desc(), DraftPick.overall.asc())
    )
    pick_res = await session.execute(picks_stmt)
    picks = list(pick_res.scalars().unique().all())

    stats_stmt = (
        select(PlayerSeasonStat)
        .where(PlayerSeasonStat.player_id == player_id)
        .order_by(PlayerSeasonStat.season.asc())
    )
    s_res = await session.execute(stats_stmt)
    stats = list(s_res.scalars().all())

    return player, picks, stats


async def get_team_draft_class(session: AsyncSession, *, team_id: int, year: int) -> tuple[Team | None, list[DraftPick]]:
    t_stmt = select(Team).where(Team.id == team_id)
    t_res = await session.execute(t_stmt)
    team = t_res.scalars().first()
    if team is None:
        return None, []

    picks_stmt = (
        select(DraftPick)
        .where(DraftPick.team_id == team_id, DraftPick.year == year)
        .options(joinedload(DraftPick.team), joinedload(DraftPick.player), joinedload(DraftPick.outcome))
        .order_by(DraftPick.overall.asc())
    )
    p_res = await session.execute(picks_stmt)
    picks = list(p_res.scalars().unique().all())
    return team, picks
