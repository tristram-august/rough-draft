from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import db_session
from app.mappers import pick_to_board_row, pick_to_detail, team_out
from app.models import DraftPick, Team
from app.repo import get_pick_detail, get_player_detail, get_team_draft_class, list_draft_board
from app.repo_votes_bulk import get_community_votes_for_picks, get_your_votes_for_picks 
from app.schemas import DraftBoardRow, PickDetail, PlayerDetail, PlayerSeasonStatOut, TeamDraftClass, VoteIn, CommunityVotesOut, VoteOut
from app.repo_votes import (
    community_votes_out,
    get_community_votes,
    get_pick_id,
    get_your_vote,
    upsert_vote,
)


router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def _anon_voter_key(x_client_id: str | None) -> str | None:
    if not x_client_id:
        return None
    x_client_id = x_client_id.strip()
    if len(x_client_id) < 8 or len(x_client_id) > 64:
        return None
    return x_client_id


@router.get("/draft", response_model=list[DraftBoardRow])
async def draft_board(
    year: int = Query(..., ge=1936, le=2100),
    round: int | None = Query(None, ge=1, le=32),
    team: str | None = Query(None, min_length=2, max_length=8),
    pos: str | None = Query(None, min_length=1, max_length=8),
    q: str | None = Query(None, min_length=1, max_length=128),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0, le=100000),
    x_client_id: str | None = Header(default=None, alias="X-Client-Id"),
    session: AsyncSession = Depends(db_session),
) -> list[DraftBoardRow]:
    picks = await list_draft_board(
        session,
        year=year,
        round=round,
        team=team,
        pos=pos,
        q=q,
        limit=limit,
        offset=offset,
    )

    traded_team_ids = {p.traded_from_team_id for p in picks if p.traded_from_team_id}
    traded_teams = {}
    if traded_team_ids:
        res = await session.execute(select(Team).where(Team.id.in_(traded_team_ids)))
        traded_teams = {t.id: t for t in res.scalars().all()}

    pick_ids = [p.id for p in picks]
    cv_map = await get_community_votes_for_picks(session, pick_ids=pick_ids)

    voter_key = _anon_voter_key(x_client_id)
    your_map: dict[int, str] = {}
    if voter_key:
        your_map = await get_your_votes_for_picks(
            session,
            pick_ids=pick_ids,
            voter_type="anon",
            voter_key=voter_key,
        )

    rows: list[DraftBoardRow] = []
    for p in picks:
        row = pick_to_board_row(p, traded_from_team=traded_teams.get(p.traded_from_team_id))
        if p.id in cv_map:
            row.community_votes = cv_map[p.id]
        else:
            row.community_votes = {"success": 0, "bust": 0, "total": 0, "community_score": 0, "community_label": "LowSignal"}
        if p.id in your_map:
            row.your_vote = {"value": your_map[p.id]}
        rows.append(row)

    return rows


@router.get("/pick/{year}/{overall}", response_model=PickDetail)
async def pick_detail(
    year: int,
    overall: int,
    x_client_id: str | None = Header(default=None, alias="X-Client-Id"),
    session: AsyncSession = Depends(db_session),
) -> PickDetail:
    pick = await get_pick_detail(session, year=year, overall=overall)
    if not pick:
        raise HTTPException(status_code=404, detail="Pick not found")

    traded_team = None
    if pick.traded_from_team_id:
        res = await session.execute(select(Team).where(Team.id == pick.traded_from_team_id))
        traded_team = res.scalars().first()

    detail = pick_to_detail(pick, traded_from_team=traded_team)

    success, bust = await get_community_votes(session, pick_id=pick.id)
    detail.community_votes = CommunityVotesOut(**community_votes_out(success, bust))

    voter_key = _anon_voter_key(x_client_id)
    if voter_key:
        val = await get_your_vote(session, pick_id=pick.id, voter_type="anon", voter_key=voter_key)
        if val:
            detail.your_vote = VoteOut(value=val)

    return detail



@router.get("/player/{player_id}", response_model=PlayerDetail)
async def player_detail(
    player_id: int,
    session: AsyncSession = Depends(db_session),
) -> PlayerDetail:
    player, picks, stats = await get_player_detail(session, player_id=player_id)
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")

    return PlayerDetail(
        player={
            "id": player.id,
            "full_name": player.full_name,
            "position": player.position,
            "college": player.college,
            "birthdate": player.birthdate,
        },
        draft_picks=[pick_to_board_row(p) for p in picks],
        season_stats=[
            PlayerSeasonStatOut(
                season=s.season,
                team_id=s.team_id,
                games=s.games,
                starts=s.starts,
                note=s.note,
            )
            for s in stats
        ],
    )


@router.get("/team/{team_id}", response_model=TeamDraftClass)
async def team_draft_class(
    team_id: int,
    year: int = Query(..., ge=1936, le=2100),
    session: AsyncSession = Depends(db_session),
) -> TeamDraftClass:
    team, picks = await get_team_draft_class(session, team_id=team_id, year=year)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")
    return TeamDraftClass(team=team_out(team), year=year, picks=[pick_to_board_row(p) for p in picks])

def _anon_voter_key(x_client_id: str | None) -> str | None:
    if not x_client_id:
        return None
    x_client_id = x_client_id.strip()
    if len(x_client_id) < 8 or len(x_client_id) > 64:
        return None
    return x_client_id

@router.post("/pick/{year}/{overall}/vote", response_model=CommunityVotesOut)
async def vote_on_pick(
    year: int,
    overall: int,
    payload: VoteIn,
    x_client_id: str | None = Header(default=None, alias="X-Client-Id"),
    session: AsyncSession = Depends(db_session),
) -> CommunityVotesOut:
    voter_key = _anon_voter_key(x_client_id)
    if not voter_key:
        raise HTTPException(status_code=400, detail="Missing/invalid X-Client-Id")

    pick_id = await get_pick_id(session, year=year, overall=overall)
    if not pick_id:
        raise HTTPException(status_code=404, detail="Pick not found")

    await upsert_vote(
        session,
        pick_id=pick_id,
        voter_type="anon",
        voter_key=voter_key,
        value=payload.value,
    )
    await session.commit()

    success, bust = await get_community_votes(session, pick_id=pick_id)
    return CommunityVotesOut(**community_votes_out(success, bust))

