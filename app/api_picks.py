"""
Straight-up game picks with weekly and season standings.

Anonymous picks work the same way draft-board voting does: an X-Client-Id header
identifies the voter. Signed-in users are keyed by user id instead, so signing in
gives you a stable identity across devices.
"""
from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_optional_user
from app.db import db_session
from app.models import Game, GamePick, GamePrediction, Team, User
from app.schemas import (
    PickIn,
    PickLeaderRow,
    PickLeaderboardOut,
    PickSplitOut,
    SlateGameOut,
    SlateOut,
)

router = APIRouter(tags=["picks"])

# nflverse gametime is US/Eastern wall clock.
EASTERN = ZoneInfo("America/New_York")


def _anon_voter_key(x_client_id: str | None) -> str | None:
    if not x_client_id:
        return None
    x_client_id = x_client_id.strip()
    if len(x_client_id) < 8 or len(x_client_id) > 64:
        return None
    return x_client_id


def _identity(
    current_user: User | None, x_client_id: str | None
) -> tuple[str, str] | tuple[None, None]:
    """Signed-in identity wins over the anonymous client id."""
    if current_user is not None:
        return "user", str(current_user.id)
    key = _anon_voter_key(x_client_id)
    if key is None:
        return None, None
    return "anon", key


def kickoff_et(game: Game) -> datetime | None:
    """Timezone-aware kickoff. Games with no date can't be locked."""
    if game.gameday is None:
        return None
    hour, minute = 0, 0
    if game.gametime:
        try:
            parts = game.gametime.split(":")
            hour, minute = int(parts[0]), int(parts[1])
        except (ValueError, IndexError):
            hour, minute = 0, 0
    return datetime.combine(game.gameday, time(hour, minute), tzinfo=EASTERN)


def is_locked(game: Game, now: datetime | None = None) -> bool:
    kickoff = kickoff_et(game)
    if kickoff is None:
        # No scheduled time, but a final score means it's certainly over.
        return game.home_score is not None
    return (now or datetime.now(EASTERN)) >= kickoff


def winner_of(game: Game) -> str | None:
    """Winning team abbrev, or None if unfinished or tied."""
    if game.home_score is None or game.away_score is None:
        return None
    if game.home_score > game.away_score:
        return game.home_team
    if game.away_score > game.home_score:
        return game.away_team
    return None


async def _resolve_slate(session: AsyncSession, season: int | None, week: int | None):
    """Explicit season+week, else the next upcoming slate."""
    if season is not None and week is not None:
        return season, week

    from datetime import date

    today = date.today()
    stmt = (
        select(Game.season, Game.week)
        .where(Game.gameday.is_not(None), Game.gameday >= today)
        .order_by(Game.gameday, Game.game_id)
        .limit(1)
    )
    row = (await session.execute(stmt)).first()
    if row is None:
        # Season's over — fall back to the most recent slate played.
        stmt = (
            select(Game.season, Game.week)
            .where(Game.gameday.is_not(None))
            .order_by(Game.gameday.desc(), Game.game_id)
            .limit(1)
        )
        row = (await session.execute(stmt)).first()
    if row is None:
        return None, None
    return int(row[0]), int(row[1]) if row[1] is not None else None


@router.get("/picks/slate", response_model=SlateOut)
async def picks_slate(
    season: int | None = Query(default=None),
    week: int | None = Query(default=None),
    x_client_id: str | None = Header(default=None, alias="X-Client-Id"),
    current_user: User | None = Depends(get_optional_user),
    session: AsyncSession = Depends(db_session),
) -> SlateOut:
    season, week = await _resolve_slate(session, season, week)
    if season is None:
        return SlateOut(games=[])

    games = (
        await session.execute(
            select(Game)
            .where(Game.season == season, Game.week == week)
            .order_by(Game.gameday, Game.gametime, Game.game_id)
        )
    ).scalars().all()
    if not games:
        return SlateOut(season=season, week=week, games=[])

    game_ids = [g.game_id for g in games]

    # Community split, one row per (game, team).
    split_rows = (
        await session.execute(
            select(GamePick.game_id, GamePick.picked_team, func.count())
            .where(GamePick.game_id.in_(game_ids))
            .group_by(GamePick.game_id, GamePick.picked_team)
        )
    ).all()
    splits: dict[str, dict[str, int]] = {}
    for gid, team, count in split_rows:
        splits.setdefault(gid, {})[team] = int(count)

    voter_type, voter_key = _identity(current_user, x_client_id)
    yours: dict[str, str] = {}
    if voter_type is not None:
        rows = (
            await session.execute(
                select(GamePick.game_id, GamePick.picked_team).where(
                    GamePick.game_id.in_(game_ids),
                    GamePick.voter_type == voter_type,
                    GamePick.voter_key == voter_key,
                )
            )
        ).all()
        yours = {gid: team for gid, team in rows}

    team_names = {
        abbrev: name for abbrev, name in (await session.execute(select(Team.abbrev, Team.name))).all()
    }

    predictions = {
        p.game_id: p
        for p in (
            await session.execute(select(GamePrediction).where(GamePrediction.game_id.in_(game_ids)))
        ).scalars()
    }

    now = datetime.now(EASTERN)
    out: list[SlateGameOut] = []
    for g in games:
        by_team = splits.get(g.game_id, {})
        away_n, home_n = by_team.get(g.away_team, 0), by_team.get(g.home_team, 0)
        win = winner_of(g)
        pick = yours.get(g.game_id)

        result = None
        if pick is not None and g.home_score is not None and g.away_score is not None:
            result = "push" if win is None else ("win" if pick == win else "loss")

        pred = predictions.get(g.game_id)

        out.append(
            SlateGameOut(
                game_id=g.game_id,
                season=g.season,
                game_type=g.game_type,
                week=g.week,
                gameday=g.gameday,
                weekday=g.weekday,
                gametime=g.gametime,
                kickoff_et=kickoff_et(g),
                away_team=g.away_team,
                home_team=g.home_team,
                away_name=team_names.get(g.away_team),
                home_name=team_names.get(g.home_team),
                away_score=g.away_score,
                home_score=g.home_score,
                final=g.home_score is not None and g.away_score is not None,
                spread_line=g.spread_line,
                total_line=g.total_line,
                div_game=g.div_game,
                stadium=g.stadium,
                locked=is_locked(g, now),
                your_pick=pick,
                split=PickSplitOut(away=away_n, home=home_n, total=away_n + home_n),
                winner=win,
                your_result=result,
                model_home_win_prob=pred.home_win_prob if pred else None,
                model_favorite=pred.predicted_winner if pred else None,
            )
        )

    return SlateOut(season=season, week=week, game_type=games[0].game_type, games=out)


@router.put("/picks/{game_id}", response_model=SlateGameOut)
async def make_pick(
    game_id: str,
    payload: PickIn,
    x_client_id: str | None = Header(default=None, alias="X-Client-Id"),
    current_user: User | None = Depends(get_optional_user),
    session: AsyncSession = Depends(db_session),
) -> SlateGameOut:
    voter_type, voter_key = _identity(current_user, x_client_id)
    if voter_type is None:
        raise HTTPException(status_code=400, detail="Missing X-Client-Id header")

    game = (
        await session.execute(select(Game).where(Game.game_id == game_id))
    ).scalars().first()
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    picked = payload.picked_team.strip().upper()
    if picked not in (game.home_team, game.away_team):
        raise HTTPException(status_code=400, detail="That team isn't playing in this game")

    # The whole point: no picking a game that already kicked off.
    if is_locked(game):
        raise HTTPException(status_code=409, detail="This game is locked")

    existing = (
        await session.execute(
            select(GamePick).where(
                GamePick.game_id == game_id,
                GamePick.voter_type == voter_type,
                GamePick.voter_key == voter_key,
            )
        )
    ).scalars().first()

    if existing:
        existing.picked_team = picked
    else:
        session.add(
            GamePick(
                game_id=game_id,
                voter_type=voter_type,
                voter_key=voter_key,
                picked_team=picked,
            )
        )
    await session.commit()

    counts = (
        await session.execute(
            select(GamePick.picked_team, func.count())
            .where(GamePick.game_id == game_id)
            .group_by(GamePick.picked_team)
        )
    ).all()
    by_team = {team: int(n) for team, n in counts}
    away_n, home_n = by_team.get(game.away_team, 0), by_team.get(game.home_team, 0)

    team_names = {
        abbrev: name for abbrev, name in (await session.execute(select(Team.abbrev, Team.name))).all()
    }

    return SlateGameOut(
        game_id=game.game_id,
        season=game.season,
        game_type=game.game_type,
        week=game.week,
        gameday=game.gameday,
        weekday=game.weekday,
        gametime=game.gametime,
        kickoff_et=kickoff_et(game),
        away_team=game.away_team,
        home_team=game.home_team,
        away_name=team_names.get(game.away_team),
        home_name=team_names.get(game.home_team),
        away_score=game.away_score,
        home_score=game.home_score,
        final=game.home_score is not None and game.away_score is not None,
        spread_line=game.spread_line,
        total_line=game.total_line,
        div_game=game.div_game,
        stadium=game.stadium,
        locked=False,
        your_pick=picked,
        split=PickSplitOut(away=away_n, home=home_n, total=away_n + home_n),
        winner=winner_of(game),
        your_result=None,
    )


@router.get("/picks/leaderboard", response_model=PickLeaderboardOut)
async def picks_leaderboard(
    season: int = Query(...),
    week: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    x_client_id: str | None = Header(default=None, alias="X-Client-Id"),
    current_user: User | None = Depends(get_optional_user),
    session: AsyncSession = Depends(db_session),
) -> PickLeaderboardOut:
    winner_expr = case(
        (Game.home_score > Game.away_score, Game.home_team),
        (Game.away_score > Game.home_score, Game.away_team),
        else_=None,
    )
    is_push = Game.home_score == Game.away_score
    is_win = GamePick.picked_team == winner_expr

    filters = [Game.season == season, Game.home_score.is_not(None), Game.away_score.is_not(None)]
    if week is not None:
        filters.append(Game.week == week)

    wins = func.sum(case((is_win, 1), else_=0)).label("wins")
    pushes = func.sum(case((is_push, 1), else_=0)).label("pushes")
    graded = func.count().label("graded")

    stmt = (
        select(GamePick.voter_type, GamePick.voter_key, wins, pushes, graded)
        .join(Game, Game.game_id == GamePick.game_id)
        .where(*filters)
        .group_by(GamePick.voter_type, GamePick.voter_key)
        .order_by(wins.desc(), graded.desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()

    # Resolve usernames for signed-in entrants.
    user_ids = [int(k) for t, k, *_ in rows if t == "user" and k.isdigit()]
    usernames: dict[str, str] = {}
    if user_ids:
        name_rows = (
            await session.execute(select(User.id, User.username).where(User.id.in_(user_ids)))
        ).all()
        usernames = {str(uid): name for uid, name in name_rows}

    my_type, my_key = _identity(current_user, x_client_id)

    out: list[PickLeaderRow] = []
    for i, (voter_type, voter_key, w, p, g) in enumerate(rows):
        w, p, g = int(w or 0), int(p or 0), int(g or 0)
        losses = max(0, g - w - p)
        decided = w + losses
        if voter_type == "user":
            display = usernames.get(voter_key, f"User {voter_key}")
        else:
            # Trailing chars, not leading: client ids often share a prefix, which
            # would render every guest with the same name.
            display = f"Guest {voter_key[-4:]}"
        out.append(
            PickLeaderRow(
                rank=i + 1,
                display_name=display,
                voter_type=voter_type,
                is_you=(voter_type == my_type and voter_key == my_key),
                wins=w,
                losses=losses,
                pushes=p,
                graded=g,
                pct=round(w / decided, 3) if decided else 0.0,
            )
        )

    return PickLeaderboardOut(
        season=season,
        week=week,
        scope="week" if week is not None else "season",
        rows=out,
    )
