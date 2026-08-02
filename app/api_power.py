"""
Power rankings — teams 1–32, or players within a position.

One set of endpoints serves both. `subject_type` picks the pool (team vs player)
and `subject_group` narrows players to a position, so adding RB or WR rankings
later is a query-string change, not a migration.

The official ranking is the site's editorial list. Every other ballot is a user's,
and the consensus column is the mean rank across those.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.auth import get_current_user, get_optional_user
from app.db import db_session
from app.models import (
    PlayerDim,
    PlayerGameStat,
    PowerRanking,
    PowerRankingEntry,
    Team,
    User,
)
from app.schemas import (
    PowerBallotIn,
    PowerEntryOut,
    PowerRankingOut,
    PowerScopeOut,
    PowerSubjectOut,
)

router = APIRouter(tags=["power"])

SUBJECT_TYPES = ("team", "player")
# Positions we'll rank individually. QB first, per the roadmap.
RANKABLE_POSITIONS = ("QB", "RB", "WR", "TE")
PLAYER_POOL_LIMIT = 40

# player_dim.latest_team carries nflverse codes; the team table uses LAR.
TEAM_CODE_FIXES = {"LA": "LAR", "STL": "LAR", "OAK": "LV", "SD": "LAC"}


def _normalize_scope(subject_type: str, subject_group: str) -> tuple[str, str]:
    subject_type = subject_type.strip().lower()
    if subject_type not in SUBJECT_TYPES:
        raise HTTPException(status_code=400, detail="Unknown subject type")

    group = (subject_group or "").strip().upper()
    if subject_type == "team":
        return subject_type, ""
    if group not in RANKABLE_POSITIONS:
        raise HTTPException(status_code=400, detail="Unknown position group")
    return subject_type, group


async def _team_subjects(session: AsyncSession) -> dict[str, PowerSubjectOut]:
    rows = (
        await session.execute(
            select(Team.abbrev, Team.name, Team.city, Team.conference, Team.division).order_by(
                Team.abbrev
            )
        )
    ).all()
    return {
        abbrev: PowerSubjectOut(
            subject_id=abbrev,
            name=f"{city} {name}".strip(),
            subtitle=f"{conference} {division}".strip() if conference else None,
        )
        for abbrev, name, city, conference, division in rows
    }


async def _player_subjects(
    session: AsyncSession, position: str, season: int
) -> dict[str, PowerSubjectOut]:
    """
    Recent starters at a position, busiest first — ranking a pool of 60 backups
    isn't useful, so this is capped at the players who actually played.
    """
    volume = func.sum(
        func.coalesce(PlayerGameStat.pass_attempts, 0)
        + func.coalesce(PlayerGameStat.rush_attempts, 0)
        + func.coalesce(PlayerGameStat.targets, 0)
    ).label("volume")

    stmt = (
        select(PlayerDim.gsis_id, PlayerDim.display_name, PlayerDim.latest_team, PlayerDim.headshot, volume)
        .join(PlayerGameStat, PlayerGameStat.player_gsis_id == PlayerDim.gsis_id)
        .where(
            PlayerDim.position == position,
            PlayerGameStat.season >= season - 1,
        )
        .group_by(PlayerDim.gsis_id, PlayerDim.display_name, PlayerDim.latest_team, PlayerDim.headshot)
        .order_by(volume.desc())
        .limit(PLAYER_POOL_LIMIT)
    )
    rows = (await session.execute(stmt)).all()
    return {
        gsis_id: PowerSubjectOut(
            subject_id=gsis_id,
            name=display_name or gsis_id,
            subtitle=TEAM_CODE_FIXES.get(latest_team or "", latest_team),
            image=headshot,
        )
        for gsis_id, display_name, latest_team, headshot, _ in rows
    }


async def _subjects(
    session: AsyncSession, subject_type: str, subject_group: str, season: int
) -> dict[str, PowerSubjectOut]:
    if subject_type == "team":
        return await _team_subjects(session)
    return await _player_subjects(session, subject_group, season)


async def _load_ballots(
    session: AsyncSession, subject_type: str, subject_group: str, season: int, week: int | None
) -> list[PowerRanking]:
    stmt = (
        select(PowerRanking)
        .options(joinedload(PowerRanking.author))
        .where(
            PowerRanking.subject_type == subject_type,
            PowerRanking.subject_group == subject_group,
            PowerRanking.season == season,
            PowerRanking.week.is_(None) if week is None else PowerRanking.week == week,
        )
    )
    return list((await session.execute(stmt)).unique().scalars().all())


@router.get("/power/subjects", response_model=list[PowerSubjectOut])
async def power_subjects(
    subject_type: str = Query(default="team"),
    subject_group: str = Query(default=""),
    season: int = Query(default=2026),
    session: AsyncSession = Depends(db_session),
) -> list[PowerSubjectOut]:
    subject_type, subject_group = _normalize_scope(subject_type, subject_group)
    subjects = await _subjects(session, subject_type, subject_group, season)
    return list(subjects.values())


@router.get("/power/positions", response_model=list[str])
async def power_positions() -> list[str]:
    return list(RANKABLE_POSITIONS)


@router.get("/power/scopes", response_model=list[PowerScopeOut])
async def power_scopes(
    subject_type: str = Query(default="team"),
    subject_group: str = Query(default=""),
    session: AsyncSession = Depends(db_session),
) -> list[PowerScopeOut]:
    subject_type, subject_group = _normalize_scope(subject_type, subject_group)
    stmt = (
        select(
            PowerRanking.season,
            PowerRanking.week,
            func.bool_or(PowerRanking.is_official).label("has_official"),
            func.count().label("ballots"),
        )
        .where(
            PowerRanking.subject_type == subject_type,
            PowerRanking.subject_group == subject_group,
        )
        .group_by(PowerRanking.season, PowerRanking.week)
        .order_by(PowerRanking.season.desc(), PowerRanking.week.desc().nulls_last())
    )
    rows = (await session.execute(stmt)).all()
    return [
        PowerScopeOut(
            season=int(season),
            week=int(week) if week is not None else None,
            has_official=bool(has_official),
            ballot_count=int(ballots),
        )
        for season, week, has_official, ballots in rows
    ]


@router.get("/power/rankings", response_model=PowerRankingOut)
async def power_rankings(
    subject_type: str = Query(default="team"),
    subject_group: str = Query(default=""),
    season: int = Query(...),
    week: int | None = Query(default=None),
    session: AsyncSession = Depends(db_session),
    current_user: User | None = Depends(get_optional_user),
) -> PowerRankingOut:
    subject_type, subject_group = _normalize_scope(subject_type, subject_group)
    subjects = await _subjects(session, subject_type, subject_group, season)
    ballots = await _load_ballots(session, subject_type, subject_group, season, week)

    official = next((b for b in ballots if b.is_official), None)
    user_ballots = [b for b in ballots if not b.is_official]
    yours = next((b for b in ballots if current_user and b.author_id == current_user.id), None)

    # Consensus = mean rank across user ballots.
    totals: dict[str, list[int]] = {}
    for ballot in user_ballots:
        for entry in ballot.entries:
            totals.setdefault(entry.subject_id, []).append(entry.rank)
    consensus = {sid: sum(ranks) / len(ranks) for sid, ranks in totals.items() if ranks}

    # Previous week's official list drives the movement arrows.
    previous: dict[str, int] = {}
    if week is not None and week > 1:
        prior = await _load_ballots(session, subject_type, subject_group, season, week - 1)
        prior_official = next((b for b in prior if b.is_official), None)
        if prior_official:
            previous = {e.subject_id: e.rank for e in prior_official.entries}

    your_ranks = {e.subject_id: e.rank for e in yours.entries} if yours else {}

    if official:
        ordered = sorted(official.entries, key=lambda e: e.rank)
        rows = [(e.rank, e.subject_id, e.note) for e in ordered]
    elif consensus:
        # No editorial list yet — fall back to showing the consensus itself.
        ordered_ids = sorted(consensus, key=lambda sid: consensus[sid])
        rows = [(i + 1, sid, None) for i, sid in enumerate(ordered_ids)]
    else:
        rows = []

    entries: list[PowerEntryOut] = []
    for rank, subject_id, note in rows:
        subject = subjects.get(subject_id)
        prev = previous.get(subject_id)
        entries.append(
            PowerEntryOut(
                rank=rank,
                subject_id=subject_id,
                name=subject.name if subject else subject_id,
                subtitle=subject.subtitle if subject else None,
                image=subject.image if subject else None,
                note=note,
                previous_rank=prev,
                movement=(prev - rank) if prev is not None else None,
                consensus_rank=round(consensus[subject_id], 2) if subject_id in consensus else None,
                consensus_ballots=len(totals.get(subject_id, [])),
                your_rank=your_ranks.get(subject_id),
            )
        )

    return PowerRankingOut(
        subject_type=subject_type,  # type: ignore[arg-type]
        subject_group=subject_group,
        season=season,
        week=week,
        has_official=official is not None,
        author_username=official.author.username if official else None,
        updated_at=official.updated_at if official else None,
        ballot_count=len(user_ballots),
        entries=entries,
    )


@router.get("/power/mine", response_model=list[str])
async def my_ballot(
    subject_type: str = Query(default="team"),
    subject_group: str = Query(default=""),
    season: int = Query(...),
    week: int | None = Query(default=None),
    official: bool = Query(default=False),
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> list[str]:
    """
    Your saved order, best first, for editing.

    If this exact week has nothing yet, falls back to your closest prior week
    in the same season (preseason counts as earliest) — week-to-week movement
    is usually incremental, so a new week should start from your last ballot
    instead of an unranked list. Only an exact match is used for a scope with
    nothing earlier than it (preseason itself has no fallback).
    """
    subject_type, subject_group = _normalize_scope(subject_type, subject_group)

    if official and not current_user.is_mod:
        raise HTTPException(status_code=403, detail="Mod access required")

    # Every ballot of this author's for the scope, any week, so the closest
    # prior one can be found without a query per week walked back.
    filters = [
        PowerRanking.subject_type == subject_type,
        PowerRanking.subject_group == subject_group,
        PowerRanking.season == season,
        PowerRanking.is_official == official,
    ]
    if not official:
        filters.append(PowerRanking.author_id == current_user.id)

    ballots = list((await session.execute(select(PowerRanking).where(*filters))).scalars().all())

    def chrono(b: PowerRanking) -> int:
        return -1 if b.week is None else b.week  # preseason sorts first

    target = next((b for b in ballots if b.week == week), None)
    if target is None and week is not None:
        earlier = [b for b in ballots if chrono(b) < week]
        target = max(earlier, key=chrono, default=None)

    if target is None:
        return []
    return [e.subject_id for e in sorted(target.entries, key=lambda e: e.rank)]


@router.put("/power/mine", response_model=PowerRankingOut)
async def save_ballot(
    payload: PowerBallotIn,
    subject_type: str = Query(default="team"),
    subject_group: str = Query(default=""),
    season: int = Query(...),
    week: int | None = Query(default=None),
    official: bool = Query(default=False),
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> PowerRankingOut:
    subject_type, subject_group = _normalize_scope(subject_type, subject_group)

    if official and not current_user.is_mod:
        raise HTTPException(status_code=403, detail="Mod access required")

    subjects = await _subjects(session, subject_type, subject_group, season)
    unknown = [sid for sid in payload.subject_ids if sid not in subjects]
    if unknown:
        raise HTTPException(status_code=400, detail=f"Not rankable here: {', '.join(unknown[:5])}")

    ballots = await _load_ballots(session, subject_type, subject_group, season, week)
    if official:
        ranking = next((b for b in ballots if b.is_official), None)
    else:
        ranking = next((b for b in ballots if b.author_id == current_user.id and not b.is_official), None)

    if ranking is None:
        ranking = PowerRanking(
            subject_type=subject_type,
            subject_group=subject_group,
            season=season,
            week=week,
            author_id=current_user.id,
            is_official=official,
            entries=[
                PowerRankingEntry(
                    rank=i + 1, subject_id=sid, note=payload.notes.get(sid) or None
                )
                for i, sid in enumerate(payload.subject_ids)
            ],
        )
        session.add(ranking)
    else:
        # Replace wholesale — ranks are positional, so a diff buys nothing.
        ranking.entries.clear()
        await session.flush()
        for i, sid in enumerate(payload.subject_ids):
            ranking.entries.append(
                PowerRankingEntry(rank=i + 1, subject_id=sid, note=payload.notes.get(sid) or None)
            )
        ranking.updated_at = datetime.now()

    await session.commit()

    return await power_rankings(
        subject_type=subject_type,
        subject_group=subject_group,
        season=season,
        week=week,
        session=session,
        current_user=current_user,
    )
