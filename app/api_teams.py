"""
Team-level box score stats (see scripts/ingest_team_stats.py) -- offensive
and defensive EPA/play, yardage, and turnovers, aggregated across a season or
narrowed to one week. A team's defensive EPA/plays-faced numbers come from
its *opponent's* own row for the same game_id (that opponent's offensive
output that game is exactly what this team's defense allowed) -- see
TeamGameStat's docstring in app/models.py.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.db import db_session
from app.models import Game, Team, TeamGameStat
from app.schemas import TeamGameLogRow, TeamMetric, TeamProfileOut, TeamStatRow, TeamStatsOut

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
    # fumbles_lost_total / fumble_recovery_opp arrived in migration 0021; until a
    # season is re-ingested they're NULL, so fall back to the older columns.
    giveaways = func.coalesce(t.passing_interceptions, 0) + func.coalesce(
        t.fumbles_lost_total,
        func.coalesce(t.sack_fumbles_lost, 0)
        + func.coalesce(t.rushing_fumbles_lost, 0)
        + func.coalesce(t.receiving_fumbles_lost, 0),
    )
    takeaways = func.coalesce(t.def_interceptions, 0) + func.coalesce(
        t.fumble_recovery_opp, func.coalesce(t.def_fumbles_forced, 0)
    )
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


# ── Single-team drill-down ────────────────────────────────────────────────────

_SUM_COLS = [c.name for c in TeamGameStat.__table__.columns
             if c.name not in ("id", "season", "week", "season_type", "game_id", "team", "opponent_team")]


def _n(v: Any) -> float:
    return float(v) if v is not None else 0.0


def _giveaways(r: TeamGameStat) -> float:
    fumbles = r.fumbles_lost_total if r.fumbles_lost_total is not None else (
        _n(r.sack_fumbles_lost) + _n(r.rushing_fumbles_lost) + _n(r.receiving_fumbles_lost))
    return _n(r.passing_interceptions) + _n(fumbles)


def _takeaways(r: TeamGameStat) -> float:
    fumbles = r.fumble_recovery_opp if r.fumble_recovery_opp is not None else r.def_fumbles_forced
    return _n(r.def_interceptions) + _n(fumbles)


def _div(a: float, b: float) -> float | None:
    return a / b if b else None


class _Agg:
    """Season totals for one team: its own box-score sums and its opponents' (what its defense allowed)."""

    def __init__(self) -> None:
        self.own: dict[str, float] = defaultdict(float)
        self.opp: dict[str, float] = defaultdict(float)
        self.games = 0
        self.points_for = 0
        self.points_against = 0

    def add(self, row: TeamGameStat, opp: TeamGameStat | None, pf: int | None, pa: int | None) -> None:
        self.games += 1
        self.points_for += pf or 0
        self.points_against += pa or 0
        for c in _SUM_COLS:
            self.own[c] += _n(getattr(row, c))
            if opp is not None:
                self.opp[c] += _n(getattr(opp, c))
        self.own["giveaways"] += _giveaways(row)
        self.own["takeaways"] += _takeaways(row)


def _plays(s: dict[str, float]) -> float:
    return s["attempts"] + s["carries"]


def _epa(s: dict[str, float]) -> float:
    return s["passing_epa"] + s["rushing_epa"]


def _ypp(s: dict[str, float]) -> float | None:
    yards = s["passing_yards"] + s["sack_yards_lost"] + s["rushing_yards"]  # sack_yards_lost is negative
    return _div(yards, s["attempts"] + s["sacks_suffered"] + s["carries"])


def _fg_range(s: dict[str, float], buckets: tuple[str, ...]) -> tuple[float, float]:
    made = sum(s[f"fg_made_{b}"] for b in buckets)
    return made, made + sum(s[f"fg_missed_{b}"] for b in buckets)


def _signed(fmt: str) -> Callable[[float], str]:
    return lambda v: ("+" if v > 0 else "") + format(v, fmt)


_pct = lambda v: f"{v * 100:.1f}%"  # noqa: E731
_f1 = lambda v: f"{v:.1f}"  # noqa: E731
_f0 = lambda v: f"{v:.0f}"  # noqa: E731

# (key, label, value(agg), formatter, better, note)
MetricSpec = tuple[str, str, Callable[[_Agg], float | None], Callable[[float], str], str | None, str | None]

SUMMARY: list[MetricSpec] = [
    ("off_epa_per_play", "Offense EPA/play", lambda a: _div(_epa(a.own), _plays(a.own)), _signed(".3f"), "high", None),
    ("def_epa_per_play", "Defense EPA/play allowed", lambda a: _div(_epa(a.opp), _plays(a.opp)), _signed(".3f"), "low", None),
    ("point_diff_pg", "Point differential / game", lambda a: _div(a.points_for - a.points_against, a.games), _signed(".1f"), "high", None),
    ("turnover_margin", "Turnover margin", lambda a: a.own["takeaways"] - a.own["giveaways"], _signed(".0f"), "high", None),
]

OFFENSE: list[MetricSpec] = [
    ("points_pg", "Points / game", lambda a: _div(a.points_for, a.games), _f1, "high", None),
    ("yards_per_play", "Yards / play", lambda a: _ypp(a.own), _f1, "high", "Sacks count as plays"),
    ("pass_yards_pg", "Pass yards / game", lambda a: _div(a.own["passing_yards"], a.games), _f0, "high", None),
    ("rush_yards_pg", "Rush yards / game", lambda a: _div(a.own["rushing_yards"], a.games), _f0, "high", None),
    ("explosive_pg", "Explosive plays / game", lambda a: _div(a.own["passing_20"] + a.own["rushing_20"], a.games), _f1, "high", "Completions and runs of 20+ yards"),
    ("first_downs_pg", "First downs / game", lambda a: _div(a.own["passing_first_downs"] + a.own["rushing_first_downs"], a.games), _f1, "high", None),
    ("sacks_allowed_pg", "Sacks allowed / game", lambda a: _div(a.own["sacks_suffered"], a.games), _f1, "low", None),
    ("giveaways_pg", "Giveaways / game", lambda a: _div(a.own["giveaways"], a.games), _f1, "low", "Interceptions + lost fumbles, incl. special teams"),
    ("pass_rate", "Pass rate", lambda a: _div(a.own["attempts"] + a.own["sacks_suffered"], a.own["attempts"] + a.own["sacks_suffered"] + a.own["carries"]), _pct, None, "Dropbacks as a share of plays — style, not quality"),
    ("adot", "Avg depth of target", lambda a: _div(a.own["passing_air_yards"], a.own["attempts"]), _f1, None, "Air yards per pass attempt"),
    ("yac_share", "YAC share of pass yards", lambda a: _div(a.own["passing_yards_after_catch"], a.own["passing_yards"]), _pct, None, None),
]

DEFENSE: list[MetricSpec] = [
    ("points_allowed_pg", "Points allowed / game", lambda a: _div(a.points_against, a.games), _f1, "low", None),
    ("yards_per_play_allowed", "Yards / play allowed", lambda a: _ypp(a.opp), _f1, "low", None),
    ("pass_yards_allowed_pg", "Pass yards allowed / game", lambda a: _div(a.opp["passing_yards"], a.games), _f0, "low", None),
    ("rush_yards_allowed_pg", "Rush yards allowed / game", lambda a: _div(a.opp["rushing_yards"], a.games), _f0, "low", None),
    ("explosive_allowed_pg", "Explosive plays allowed / game", lambda a: _div(a.opp["passing_20"] + a.opp["rushing_20"], a.games), _f1, "low", "Completions and runs of 20+ yards"),
    ("first_downs_allowed_pg", "First downs allowed / game", lambda a: _div(a.opp["passing_first_downs"] + a.opp["rushing_first_downs"], a.games), _f1, "low", None),
    ("sacks_pg", "Sacks / game", lambda a: _div(a.own["def_sacks"], a.games), _f1, "high", None),
    ("qb_hits_pg", "QB hits / game", lambda a: _div(a.own["def_qb_hits"], a.games), _f1, "high", None),
    ("takeaways_pg", "Takeaways / game", lambda a: _div(a.own["takeaways"], a.games), _f1, "high", "Interceptions + recovered opponent fumbles"),
    ("passes_defended_pg", "Passes defended / game", lambda a: _div(a.own["def_pass_defended"], a.games), _f1, "high", None),
]


def _fg_metric(buckets: tuple[str, ...]) -> Callable[[_Agg], float | None]:
    return lambda a: _div(*_fg_range(a.own, buckets))


SPECIAL: list[MetricSpec] = [
    ("fg_pct", "Field goal %", lambda a: _div(a.own["fg_made"], a.own["fg_att"]), _pct, "high", None),
    ("fg_40_pct", "Field goal % from 40+", _fg_metric(("40_49", "50_59", "60_")), _pct, "high", None),
    ("fg_long", "Longest field goal", lambda a: None, _f0, "high", None),  # filled from game max below
    ("net_punt", "Net yards / punt", lambda a: _div(a.own["pt_net_yards"], a.own["pt_att"]), _f1, "high", None),
    ("punt_inside_20", "Punts inside the 20", lambda a: _div(a.own["pt_inside_20"], a.own["pt_att"]), _pct, "high", "Share of punts"),
    ("kr_avg", "Kick return average", lambda a: _div(a.own["kickoff_return_yards"], a.own["kickoff_returns"]), _f1, "high", None),
    ("pr_avg", "Punt return average", lambda a: _div(a.own["punt_return_yards"], a.own["punt_returns"]), _f1, "high", None),
    ("penalty_yards_pg", "Penalty yards / game", lambda a: _div(a.own["penalty_yards"], a.games), _f1, "low", None),
]


def _ranked(specs: list[MetricSpec], aggs: dict[str, _Agg], team: str, overrides: dict[str, dict[str, float]]) -> list[TeamMetric]:
    out = []
    for key, label, fn, fmt, better, note in specs:
        vals = {t: overrides[key][t] if key in overrides else fn(a) for t, a in aggs.items()}
        present = {t: round(v, 6) for t, v in vals.items() if v is not None}
        mine = present.get(team)
        rank = None
        if mine is not None:
            beats = (lambda v: v < mine) if better == "low" else (lambda v: v > mine)
            rank = 1 + sum(1 for v in present.values() if beats(v))
        out.append(TeamMetric(
            key=key, label=label, value=vals.get(team), display=fmt(vals[team]) if vals.get(team) is not None else "—",
            rank=rank, of=len(present), better=better, note=note,
        ))
    return out


@router.get("/teams/{team}/profile", response_model=TeamProfileOut)
async def team_profile(
    team: str,
    season: int = Query(...),
    season_type: str = Query(default="REG", max_length=8),
    session: AsyncSession = Depends(db_session),
) -> TeamProfileOut:
    team = team.upper()
    opp = aliased(TeamGameStat)
    stmt = (
        select(TeamGameStat, opp, Game)
        .outerjoin(opp, (opp.game_id == TeamGameStat.game_id) & (opp.team == TeamGameStat.opponent_team))
        .outerjoin(Game, Game.game_id == TeamGameStat.game_id)
        .where(TeamGameStat.season == season, TeamGameStat.season_type == season_type)
        .order_by(TeamGameStat.week)
    )
    rows = (await session.execute(stmt)).all()
    if not any(r[0].team == team for r in rows):
        raise HTTPException(status_code=404, detail="No games for that team and season")

    aggs: dict[str, _Agg] = defaultdict(_Agg)
    fg_long: dict[str, float] = defaultdict(float)
    game_log: list[TeamGameLogRow] = []
    wins = losses = ties = 0
    for row, o, g in rows:
        is_home = g is not None and g.home_team == row.team
        pf = (g.home_score if is_home else g.away_score) if g else None
        pa = (g.away_score if is_home else g.home_score) if g else None
        aggs[row.team].add(row, o, pf, pa)
        fg_long[row.team] = max(fg_long[row.team], _n(row.fg_long))
        if row.team != team:
            continue
        result = None
        if pf is not None and pa is not None:
            result = "W" if pf > pa else "L" if pf < pa else "T"
            wins += result == "W"
            losses += result == "L"
            ties += result == "T"
        own_yards = _n(row.passing_yards) + _n(row.sack_yards_lost) + _n(row.rushing_yards)
        opp_yards = (_n(o.passing_yards) + _n(o.sack_yards_lost) + _n(o.rushing_yards)) if o else 0
        own_plays = _n(row.attempts) + _n(row.carries)
        opp_plays = (_n(o.attempts) + _n(o.carries)) if o else 0
        game_log.append(TeamGameLogRow(
            week=row.week, game_id=row.game_id, gameday=g.gameday.isoformat() if g and g.gameday else None,
            opponent=row.opponent_team, home=is_home, points_for=pf, points_against=pa, result=result,
            off_epa_per_play=round(v, 3) if (v := _div(_n(row.passing_epa) + _n(row.rushing_epa), own_plays)) is not None else None,
            def_epa_per_play_allowed=(
                round(v, 3) if o and (v := _div(_n(o.passing_epa) + _n(o.rushing_epa), opp_plays)) is not None else None
            ),
            yards=int(own_yards), yards_allowed=int(opp_yards),
            giveaways=int(_giveaways(row)), takeaways=int(_takeaways(row)),
        ))

    overrides = {"fg_long": {t: (v or None) for t, v in fg_long.items()}}
    mine = aggs[team]
    names = {r.abbrev: f"{r.city} {r.name}" for r in (await session.execute(select(Team.abbrev, Team.name, Team.city))).all()}
    return TeamProfileOut(
        team=team, team_name=names.get(team), season=season, season_type=season_type,
        games=mine.games, wins=wins, losses=losses, ties=ties,
        points_for=mine.points_for, points_against=mine.points_against,
        summary=_ranked(SUMMARY, aggs, team, overrides),
        offense=_ranked(OFFENSE, aggs, team, overrides),
        defense=_ranked(DEFENSE, aggs, team, overrides),
        special_teams=_ranked(SPECIAL, aggs, team, overrides),
        game_log=game_log,
    )
