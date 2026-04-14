from __future__ import annotations

from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy import select, func, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db import db_session
from app.mappers import pick_to_board_row, pick_to_detail, team_out
from app.models import DraftPick, PickVote, Team, PlayerDim, PlayerGameStat
from app.repo import get_pick_detail, get_player_detail, get_team_draft_class, list_draft_board
from app.repo_votes_bulk import get_community_votes_for_picks, get_your_votes_for_picks
from app.schemas import (
    DraftBoardRow,
    PickDetail,
    PlayerDetail,
    PlayerSeasonStatOut,
    TeamDraftClass,
    VoteIn,
    CommunityVotesOut,
    VoteOut,
)
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
        player=PlayerOut(
            id=player.id,
            full_name=player.full_name,
            position=player.position,
            college=player.college,
            birthdate=player.birthdate,
            gsis_id=player.gsis_id,
        ),
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

    existing = await get_your_vote(session, pick_id=pick_id, voter_type="anon", voter_key=voter_key)

    # IMPORTANT: depending on your repo, get_your_vote may return VoteOut, a dict, or a string.
    # Normalize it to a string value.
    existing_value = None
    if existing is None:
        existing_value = None
    elif isinstance(existing, str):
        existing_value = existing
    elif hasattr(existing, "value"):
        existing_value = getattr(existing, "value")
    elif isinstance(existing, dict):
        existing_value = existing.get("value")

    if existing_value == payload.value:
        # Toggle off: delete vote
        await session.execute(
            delete(PickVote).where(
                PickVote.pick_id == pick_id,
                PickVote.voter_type == "anon",
                PickVote.voter_key == voter_key,
            )
        )
    else:
        # Set / change vote (your existing helper)
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

@router.get("/rankings")
async def rankings(
    year: int = Query(..., ge=1936, le=2100),
    group_by: str = Query(..., pattern="^(team|player)$", alias="groupBy"),
    sort: str = Query("best", pattern="^(best|worst)$"),
    round: int | None = Query(None, ge=1, le=32),
    team: str | None = Query(None, min_length=2, max_length=8),
    pos: str | None = Query(None, min_length=1, max_length=8),
    q: str | None = Query(None, min_length=1, max_length=128),
    limit: int = Query(20, ge=1, le=50),
    min_votes: int = Query(1, ge=0, le=10_000, alias="minVotes"),
    session: AsyncSession = Depends(db_session),
) -> dict:
    """
    Rankings for:
      - groupBy=team : best teams by success ratio
      - groupBy=player + sort=best : best players by success ratio
      - groupBy=player + sort=worst: worst players by success ratio

    Uses your existing bulk vote loader: get_community_votes_for_picks().
    """

    # 1) Load scoped picks (NO pagination; year is small enough ~260 picks)
    stmt = (
        select(DraftPick)
        .options(joinedload(DraftPick.team), joinedload(DraftPick.player))
        .where(DraftPick.year == year)
    )

    if round is not None:
        stmt = stmt.where(DraftPick.round == round)

    res = await session.execute(stmt)
    picks: list[DraftPick] = list(res.scalars().all())

    # 2) Bulk community votes for these picks
    pick_ids = [p.id for p in picks]
    cv_map = await get_community_votes_for_picks(session, pick_ids=pick_ids)

    # 3) Aggregate
    # Each cv_map[pick_id] looks like: {"success": int, "bust": int, "total": int, ...}
    agg = defaultdict(lambda: {"success": 0, "bust": 0, "totalVotes": 0, "draft_team": None})

    for p in picks:
        cv = cv_map.get(p.id) or {"success": 0, "bust": 0, "total": 0}

        if group_by == "team":
            key = p.team.abbrev if p.team else str(p.team_id)
        else:
            key = p.player.full_name if p.player else str(p.player_id)
            if agg[key]["draft_team"] is None:
                agg[key]["draft_team"] = p.team.abbrev if p.team else None

        agg[key]["success"] += int(cv.get("success", 0) or 0)
        agg[key]["bust"] += int(cv.get("bust", 0) or 0)
        agg[key]["totalVotes"] += int(cv.get("total", 0) or 0)

    # 4) Convert to items with ratio
    items = []
    for label, v in agg.items():
        total = v["success"] + v["bust"]
        ratio = (v["success"] / total) if total > 0 else None
        if v["totalVotes"] < min_votes:
            continue
        item: dict = {
            ("team" if group_by == "team" else "player"): label,
            "success": v["success"],
            "bust": v["bust"],
            "totalVotes": v["totalVotes"],
            "ratio": ratio,
        }
        if group_by == "player":
            item["draft_team"] = v.get("draft_team")
        items.append(item)

    # 5) Sort + limit
    # best: higher ratio first; worst: lower ratio first
    # push None ratios to bottom always
    def sort_key(it: dict):
        r = it["ratio"]
        none_flag = 1 if r is None else 0
        # for stable ordering, also use votes desc
        return (none_flag, r if r is not None else 0.0, -it["totalVotes"])

    items.sort(key=sort_key, reverse=(sort == "best"))
    items = items[:limit]

    return {
        "year": year,
        "groupBy": group_by,
        "sort": sort,
        "limit": limit,
        "minVotes": min_votes,
        "items": items,
    }

def _scope_clause(scope: str, draft_team: str) -> Any:
    if scope == "career":
        return True
    if scope == "draft_team":
        return PlayerGameStat.team == draft_team
    if scope == "other_teams":
        return PlayerGameStat.team != draft_team
    raise ValueError(f"unknown scope: {scope}")


def _pos_group_bucket(pos_group: str | None) -> str:
    if not pos_group:
        return "OTHER"
    pg = pos_group.upper().strip()
    if pg in {"QB"}:
        return "QB"
    if pg in {"RB"}:
        return "RB"
    if pg in {"WR", "TE"}:
        return "REC"
    if pg in {"DL", "EDGE", "LB", "DB", "CB", "S"}:
        return "DEF"
    if pg in {"K", "P", "ST", "SPEC"}:
        return "ST"
    return "OTHER"


async def _get_player_dim(session: AsyncSession, gsis_id: str) -> PlayerDim | None:
    res = await session.execute(select(PlayerDim).where(PlayerDim.gsis_id == gsis_id))
    return res.scalars().first()


async def _infer_position_group(session: AsyncSession, gsis_id: str, player_dim: PlayerDim | None) -> str | None:
    if player_dim and player_dim.position_group:
        return player_dim.position_group
    res = await session.execute(
        select(PlayerGameStat.position_group)
        .where(PlayerGameStat.player_gsis_id == gsis_id, PlayerGameStat.position_group.is_not(None))
        .limit(1)
    )
    return res.scalar_one_or_none()


async def _teams_by_games(session: AsyncSession, gsis_id: str, clause: Any) -> list[dict[str, Any]]:
    q = (
        select(
            PlayerGameStat.team.label("team"),
            func.count(func.distinct(PlayerGameStat.game_id)).label("games"),
        )
        .where(PlayerGameStat.player_gsis_id == gsis_id, clause)
        .group_by(PlayerGameStat.team)
        .order_by(func.count(func.distinct(PlayerGameStat.game_id)).desc(), PlayerGameStat.team.asc())
    )
    rows = (await session.execute(q)).all()
    return [{"team": r.team, "games": int(r.games)} for r in rows if r.team]


async def _seasons_in_scope(session: AsyncSession, gsis_id: str, clause: Any) -> list[int]:
    q = (
        select(PlayerGameStat.season)
        .where(PlayerGameStat.player_gsis_id == gsis_id, clause)
        .distinct()
        .order_by(PlayerGameStat.season.asc())
    )
    rows = (await session.execute(q)).scalars().all()
    return [int(x) for x in rows if x is not None]


def _safe_int(x: Any) -> int:
    return int(x or 0)


def _safe_float(x: Any) -> float:
    return float(x or 0.0)


async def _aggregate_totals(session: AsyncSession, gsis_id: str, clause: Any) -> dict[str, Any]:
    q = select(
        func.count(func.distinct(PlayerGameStat.game_id)).label("games_distinct"),
        func.count().label("row_count"),
        func.coalesce(func.sum(PlayerGameStat.pass_attempts), 0).label("pass_att"),
        func.coalesce(func.sum(PlayerGameStat.pass_completions), 0).label("pass_cmp"),
        func.coalesce(func.sum(PlayerGameStat.pass_yards), 0).label("pass_yds"),
        func.coalesce(func.sum(PlayerGameStat.pass_tds), 0).label("pass_td"),
        func.coalesce(func.sum(PlayerGameStat.pass_ints), 0).label("pass_int"),
        func.coalesce(func.sum(PlayerGameStat.passing_epa), 0.0).label("pass_epa"),
        func.avg(PlayerGameStat.passing_cpoe).label("pass_cpoe_avg"),
        func.coalesce(func.sum(PlayerGameStat.rush_attempts), 0).label("rush_att"),
        func.coalesce(func.sum(PlayerGameStat.rush_yards), 0).label("rush_yds"),
        func.coalesce(func.sum(PlayerGameStat.rush_tds), 0).label("rush_td"),
        func.coalesce(func.sum(PlayerGameStat.rushing_epa), 0.0).label("rush_epa"),
        func.coalesce(func.sum(PlayerGameStat.targets), 0).label("tgt"),
        func.coalesce(func.sum(PlayerGameStat.receptions), 0).label("rec"),
        func.coalesce(func.sum(PlayerGameStat.rec_yards), 0).label("rec_yds"),
        func.coalesce(func.sum(PlayerGameStat.rec_tds), 0).label("rec_td"),
        func.coalesce(func.sum(PlayerGameStat.receiving_epa), 0.0).label("rec_epa"),
        func.avg(PlayerGameStat.target_share).label("tgt_share_avg"),
        func.coalesce(func.sum(PlayerGameStat.air_yards), 0).label("air_yds"),
        func.avg(PlayerGameStat.air_yards_share).label("air_share_avg"),
        func.coalesce(func.sum(PlayerGameStat.fumbles_lost), 0).label("fum_lost"),
        func.coalesce(func.sum(PlayerGameStat.def_tackles), 0).label("def_tackles"),
        func.coalesce(func.sum(PlayerGameStat.def_sacks), 0.0).label("def_sacks"),
        func.coalesce(func.sum(PlayerGameStat.def_ints), 0).label("def_ints"),
        func.coalesce(func.sum(PlayerGameStat.def_forced_fumbles), 0).label("def_ff"),
        func.coalesce(func.sum(PlayerGameStat.def_fumble_recoveries), 0).label("def_fr"),
        func.coalesce(func.sum(PlayerGameStat.def_tds), 0).label("def_td"),
    ).where(PlayerGameStat.player_gsis_id == gsis_id, clause)

    r = (await session.execute(q)).one()

    return {
        "games_distinct": _safe_int(r.games_distinct),
        "row_count": _safe_int(r.row_count),
        "totals": {
            "games": _safe_int(r.games_distinct),
            "passing": {
                "att": _safe_int(r.pass_att),
                "cmp": _safe_int(r.pass_cmp),
                "yds": _safe_int(r.pass_yds),
                "td": _safe_int(r.pass_td),
                "int": _safe_int(r.pass_int),
                "epa": _safe_float(r.pass_epa),
                "cpoe_avg": float(r.pass_cpoe_avg) if r.pass_cpoe_avg is not None else None,
            },
            "rushing": {
                "att": _safe_int(r.rush_att),
                "yds": _safe_int(r.rush_yds),
                "td": _safe_int(r.rush_td),
                "epa": _safe_float(r.rush_epa),
            },
            "receiving": {
                "targets": _safe_int(r.tgt),
                "rec": _safe_int(r.rec),
                "yds": _safe_int(r.rec_yds),
                "td": _safe_int(r.rec_td),
                "epa": _safe_float(r.rec_epa),
                "target_share_avg": float(r.tgt_share_avg) if r.tgt_share_avg is not None else None,
                "air_yards": _safe_int(r.air_yds),
                "air_yards_share_avg": float(r.air_share_avg) if r.air_share_avg is not None else None,
            },
            "defense": {
                "tackles": _safe_int(r.def_tackles),
                "sacks": float(r.def_sacks or 0.0),
                "int": _safe_int(r.def_ints),
                "ff": _safe_int(r.def_ff),
                "fr": _safe_int(r.def_fr),
                "td": _safe_int(r.def_td),
            },
            "ball_security": {"fumbles_lost": _safe_int(r.fum_lost)},
        },
    }


async def _best_season(session: AsyncSession, gsis_id: str, clause: Any, pos_bucket: str) -> dict[str, Any] | None:
    # Metric per position bucket:
    # QB: sum(passing_epa)
    # RB: sum(rush_yards)
    # REC: sum(targets)
    # DEF: splash index
    qb_metric = func.coalesce(func.sum(PlayerGameStat.passing_epa), 0.0)
    rb_metric = func.coalesce(func.sum(PlayerGameStat.rush_yards), 0)
    rec_metric = func.coalesce(func.sum(PlayerGameStat.targets), 0)
    def_metric = (
        func.coalesce(func.sum(PlayerGameStat.def_sacks), 0.0)
        + 2 * func.coalesce(func.sum(PlayerGameStat.def_ints), 0)
        + 2 * func.coalesce(func.sum(PlayerGameStat.def_tds), 0)
        + func.coalesce(func.sum(PlayerGameStat.def_forced_fumbles), 0)
    )

    metric = rec_metric
    if pos_bucket == "QB":
        metric = qb_metric
    elif pos_bucket == "RB":
        metric = rb_metric
    elif pos_bucket == "DEF":
        metric = def_metric

    q = (
        select(
            PlayerGameStat.season.label("season"),
            metric.label("metric"),
            func.coalesce(func.sum(PlayerGameStat.targets), 0).label("tgt"),
            func.coalesce(func.sum(PlayerGameStat.receptions), 0).label("rec"),
            func.coalesce(func.sum(PlayerGameStat.rec_yards), 0).label("rec_yds"),
            func.coalesce(func.sum(PlayerGameStat.rec_tds), 0).label("rec_td"),
            func.coalesce(func.sum(PlayerGameStat.rush_yards), 0).label("rush_yds"),
            func.coalesce(func.sum(PlayerGameStat.rush_tds), 0).label("rush_td"),
            func.coalesce(func.sum(PlayerGameStat.pass_yards), 0).label("pass_yds"),
            func.coalesce(func.sum(PlayerGameStat.pass_tds), 0).label("pass_td"),
            func.coalesce(func.sum(PlayerGameStat.pass_ints), 0).label("pass_int"),
        )
        .where(PlayerGameStat.player_gsis_id == gsis_id, clause)
        .group_by(PlayerGameStat.season)
        .order_by(metric.desc(), PlayerGameStat.season.desc())
        .limit(1)
    )
    row = (await session.execute(q)).first()
    if not row:
        return None

    season = int(row.season)
    if pos_bucket == "REC":
        headline = f"{season} — {_safe_int(row.tgt)} targets, {_safe_int(row.rec_yds)} yds, {_safe_int(row.rec_td)} TD"
        metrics = {"targets": _safe_int(row.tgt), "rec_yards": _safe_int(row.rec_yds), "rec_tds": _safe_int(row.rec_td)}
    elif pos_bucket == "RB":
        headline = f"{season} — {_safe_int(row.rush_yds)} rush yds, {_safe_int(row.rush_td)} TD"
        metrics = {"rush_yards": _safe_int(row.rush_yds), "rush_tds": _safe_int(row.rush_td)}
    elif pos_bucket == "QB":
        headline = f"{season} — {_safe_int(row.pass_yds)} pass yds, {_safe_int(row.pass_td)} TD, {_safe_int(row.pass_int)} INT"
        metrics = {"pass_yards": _safe_int(row.pass_yds), "pass_tds": _safe_int(row.pass_td), "pass_ints": _safe_int(row.pass_int)}
    else:
        headline = f"{season} — best season"
        metrics = {"metric": float(row.metric)}

    return {"season": season, "headline": headline, "metrics": metrics}


async def _best_game(session: AsyncSession, gsis_id: str, clause: Any, pos_bucket: str) -> dict[str, Any] | None:
    # Metric per position bucket:
    # REC: rec_yards (your preference)
    # QB: passing_epa
    # RB: rush_yards
    # DEF: splash index
    qb_metric = func.coalesce(PlayerGameStat.passing_epa, 0.0)
    rb_metric = func.coalesce(PlayerGameStat.rush_yards, 0)
    rec_metric = func.coalesce(PlayerGameStat.rec_yards, 0)
    def_metric = (
        func.coalesce(PlayerGameStat.def_sacks, 0.0)
        + 3 * func.coalesce(PlayerGameStat.def_ints, 0)
        + 6 * func.coalesce(PlayerGameStat.def_tds, 0)
        + 2 * func.coalesce(PlayerGameStat.def_forced_fumbles, 0)
        + 2 * func.coalesce(PlayerGameStat.def_fumble_recoveries, 0)
    )

    metric = rec_metric
    if pos_bucket == "QB":
        metric = qb_metric
    elif pos_bucket == "RB":
        metric = rb_metric
    elif pos_bucket == "DEF":
        metric = def_metric

    q = (
        select(
            PlayerGameStat.game_id,
            PlayerGameStat.season,
            PlayerGameStat.week,
            PlayerGameStat.season_type,
            PlayerGameStat.team,
            PlayerGameStat.opponent_team,
            PlayerGameStat.targets,
            PlayerGameStat.receptions,
            PlayerGameStat.rec_yards,
            PlayerGameStat.rec_tds,
            PlayerGameStat.rush_yards,
            PlayerGameStat.rush_tds,
            PlayerGameStat.pass_yards,
            PlayerGameStat.pass_tds,
            PlayerGameStat.pass_ints,
            PlayerGameStat.passing_epa,
            metric.label("metric"),
        )
        .where(PlayerGameStat.player_gsis_id == gsis_id, clause)
        .order_by(metric.desc(), PlayerGameStat.season.desc(), PlayerGameStat.week.desc())
        .limit(1)
    )
    row = (await session.execute(q)).first()
    if not row:
        return None

    season = int(row.season)
    week = int(row.week) if row.week is not None else None
    opp = row.opponent_team or "UNK"
    team = row.team or "UNK"
    season_type = row.season_type or "UNK"
    game_id = row.game_id

    if pos_bucket == "REC":
        headline = f"Week {week} vs {opp} — {_safe_int(row.receptions)} rec, {_safe_int(row.rec_yards)} yds, {_safe_int(row.rec_tds)} TD"
        metrics = {
            "targets": _safe_int(row.targets),
            "receptions": _safe_int(row.receptions),
            "rec_yards": _safe_int(row.rec_yards),
            "rec_tds": _safe_int(row.rec_tds),
        }
    elif pos_bucket == "RB":
        headline = f"Week {week} vs {opp} — {_safe_int(row.rush_yards)} rush yds, {_safe_int(row.rush_tds)} TD"
        metrics = {"rush_yards": _safe_int(row.rush_yards), "rush_tds": _safe_int(row.rush_tds)}
    elif pos_bucket == "QB":
        epa = float(row.passing_epa) if row.passing_epa is not None else 0.0
        headline = f"Week {week} vs {opp} — {_safe_int(row.pass_yards)} yds, {_safe_int(row.pass_tds)} TD, {_safe_int(row.pass_ints)} INT (EPA {epa:+.1f})"
        metrics = {
            "pass_yards": _safe_int(row.pass_yards),
            "pass_tds": _safe_int(row.pass_tds),
            "pass_ints": _safe_int(row.pass_ints),
            "passing_epa": epa,
        }
    else:
        headline = f"Week {week} vs {opp} — best game"
        metrics = {"metric": float(row.metric)}

    return {
        "game_id": game_id,
        "season": season,
        "week": week,
        "season_type": season_type,
        "team": team,
        "opponent_team": opp,
        "headline": headline,
        "metrics": metrics,
    }


async def _build_tab(session: AsyncSession, gsis_id: str, draft_team: str, scope: str, pos_bucket: str) -> dict[str, Any]:
    clause = _scope_clause(scope, draft_team)

    totals_blob = await _aggregate_totals(session, gsis_id, clause)
    teams_by = await _teams_by_games(session, gsis_id, clause)
    seasons = await _seasons_in_scope(session, gsis_id, clause)

    best_season = await _best_season(session, gsis_id, clause, pos_bucket)
    best_game = await _best_game(session, gsis_id, clause, pos_bucket)

    teams_sorted = [t["team"] for t in teams_by]

    title = "Career Total"
    team_filter = None
    if scope == "draft_team":
        title = "Draft Team"
        team_filter = {"equals": draft_team}
    elif scope == "other_teams":
        title = "Other Teams"
        team_filter = {"not_equals": draft_team}

    return {
        "scope": scope,
        "title": title,
        "team_filter": team_filter,
        "totals": totals_blob["totals"],
        "notables": {"best_season": best_season, "best_game": best_game},
        "meta": {
            "games_distinct": totals_blob["games_distinct"],
            "row_count": totals_blob["row_count"],
            "seasons_in_scope": seasons,
            "teams_in_scope": teams_sorted,
            "teams_in_scope_by_games": teams_by,
            "data_sources": ["player_game_stat", "player_dim"],
        },
    }


@router.get("/player/{gsis_id}/drawer")
async def player_drawer(
    gsis_id: str,
    draft_team: str = Query(..., min_length=2, max_length=8),
    session: AsyncSession = Depends(db_session),
) -> dict[str, Any]:
    draft_team = draft_team.strip().upper()

    player_dim = await _get_player_dim(session, gsis_id)

    # Make sure we have at least some stats for this player; otherwise return a 404-ish response
    exists_q = select(func.count()).select_from(PlayerGameStat).where(PlayerGameStat.player_gsis_id == gsis_id)
    stat_count = (await session.execute(exists_q)).scalar_one()
    if stat_count == 0 and player_dim is None:
        raise HTTPException(status_code=404, detail="Player not found")

    pos_group = await _infer_position_group(session, gsis_id, player_dim)
    pos_bucket = _pos_group_bucket(pos_group)

    player_payload: dict[str, Any] = {
        "gsis_id": gsis_id,
        "display_name": player_dim.display_name if player_dim else None,
        "position": player_dim.position if player_dim else None,
        "position_group": pos_group,
        "birth_date": player_dim.birth_date.isoformat() if player_dim and player_dim.birth_date else None,
        "height": player_dim.height if player_dim else None,
        "weight": player_dim.weight if player_dim else None,
        "headshot": player_dim.headshot if player_dim else None,
        "college_name": player_dim.college_name if player_dim else None,
        "latest_team": player_dim.latest_team if player_dim else None,
        "status": player_dim.status if player_dim else None,
        "years_of_experience": player_dim.years_of_experience if player_dim else None,
    }

    tabs = {
        "career": await _build_tab(session, gsis_id, draft_team, "career", pos_bucket),
        "draft_team": await _build_tab(session, gsis_id, draft_team, "draft_team", pos_bucket),
        "other_teams": await _build_tab(session, gsis_id, draft_team, "other_teams", pos_bucket),
    }

    return {
        "player": player_payload,
        "draft_context": {"draft_team": draft_team},
        "tabs": tabs,
        "ui_hints": {
            "default_tab": "career",
            "receiver_best_game_metric": "rec_yards",
            "position_aware_notables": True,
        },
    }


