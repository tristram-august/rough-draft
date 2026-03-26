from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DraftPick, Player, Team


@dataclass(frozen=True)
class DraftPickIn:
    year: int
    round: int
    pick_in_round: int
    overall: int
    team_abbrev: str
    team_city: str
    team_name: str
    player_name: str
    position: str
    college: str | None = None


async def upsert_team(session: AsyncSession, *, abbrev: str, city: str, name: str) -> Team:
    res = await session.execute(select(Team).where(Team.abbrev == abbrev))
    team = res.scalars().first()
    if team:
        team.city = city
        team.name = name
        return team
    team = Team(abbrev=abbrev, city=city, name=name)
    session.add(team)
    await session.flush()
    return team


async def upsert_player(session: AsyncSession, *, full_name: str, position: str, college: str | None) -> Player:
    res = await session.execute(select(Player).where(Player.full_name == full_name, Player.position == position))
    player = res.scalars().first()
    if player:
        player.college = college or player.college
        return player
    player = Player(full_name=full_name, position=position, college=college)
    session.add(player)
    await session.flush()
    return player


async def upsert_pick(session: AsyncSession, *, pick_in: DraftPickIn, team_id: int, player_id: int) -> DraftPick:
    res = await session.execute(select(DraftPick).where(DraftPick.year == pick_in.year, DraftPick.overall == pick_in.overall))
    pick = res.scalars().first()
    if pick:
        pick.round = pick_in.round
        pick.pick_in_round = pick_in.pick_in_round
        pick.team_id = team_id
        pick.player_id = player_id
        return pick
    pick = DraftPick(
        year=pick_in.year,
        round=pick_in.round,
        pick_in_round=pick_in.pick_in_round,
        overall=pick_in.overall,
        team_id=team_id,
        player_id=player_id,
    )
    session.add(pick)
    await session.flush()
    return pick


async def ingest_draft_year(session: AsyncSession, *, year: int, picks: Iterable[DraftPickIn]) -> int:
    """
    Ingest picks for a given year.

    Replace the caller's 'picks' with real fetched data.
    """
    count = 0
    for p in picks:
        team = await upsert_team(session, abbrev=p.team_abbrev, city=p.team_city, name=p.team_name)
        player = await upsert_player(session, full_name=p.player_name, position=p.position, college=p.college)
        await upsert_pick(session, pick_in=p, team_id=team.id, player_id=player.id)
        count += 1
    return count
