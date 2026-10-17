"""
Freeze the prop board before kickoff and grade it afterwards (prop_pick).

    python -m scripts.prop_scorecard --snapshot              # save this week's board (run before the games)
    python -m scripts.prop_scorecard --grade                 # grade every pick whose game is final
    python -m scripts.prop_scorecard --reconstruct 1-5       # backfill past weeks, labeled "reconstructed"

Weekly routine: ingest FantasyPros projections for the week, --snapshot,
and after the games (once player stats are ingested) --grade.

A snapshot can be re-run until kickoff -- it overwrites that week's ungraded
picks, never graded ones. Reconstructed rows never overwrite a snapshot.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert

from app.api_betting import build_board, upcoming_board_week
from app.db import get_sessionmaker
from app.models import Game, PlayerGameStat, PropPick

STAT_COLUMN = {
    "rec_yards": "rec_yards", "receptions": "receptions", "rec_tds": "rec_tds",
    "rush_yards": "rush_yards", "rush_attempts": "rush_attempts", "rush_tds": "rush_tds",
    "pass_yards": "pass_yards", "pass_attempts": "pass_attempts", "pass_tds": "pass_tds",
    "interceptions": "pass_ints",
}
UPDATABLE = ["name", "position", "team", "opponent", "line", "projection", "p_over", "mean", "source", "created_at"]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--season", type=int, default=2026)
    p.add_argument("--snapshot", action="store_true")
    p.add_argument("--week", type=int, default=None, help="Week to snapshot (defaults to the upcoming week).")
    p.add_argument("--reconstruct", type=str, default=None, help="Week or range, e.g. 3 or 1-5.")
    p.add_argument("--grade", action="store_true")
    return p.parse_args()


def _payload(board, source: str) -> list[dict]:
    now = datetime.now(timezone.utc)
    return [
        dict(
            season=board.season, week=board.week, gsis_id=r.gsis_id, name=r.name[:128], position=r.position,
            team=r.team, opponent=r.opponent, stat=r.stat, line=r.line, projection=r.projection,
            p_over=r.p_over, mean=r.mean, source=source, created_at=now,
        )
        for r in board.rows
    ]


async def snapshot(session, season: int, week: int | None) -> None:
    week = week or await upcoming_board_week(session, season)
    board = await build_board(session, season, week)
    rows = _payload(board, "snapshot")
    for i in range(0, len(rows), 500):
        stmt = insert(PropPick).values(rows[i : i + 500])
        stmt = stmt.on_conflict_do_update(
            constraint="uq_prop_pick",
            set_={c: stmt.excluded[c] for c in UPDATABLE},
            where=PropPick.result.is_(None),
        )
        await session.execute(stmt)
    await session.commit()
    print(f"Snapshot {season} week {week}: {len(rows)} picks (games not yet played)")


async def reconstruct(session, season: int, weeks: list[int]) -> None:
    for week in weeks:
        board = await build_board(session, season, week, include_final=True)
        rows = _payload(board, "reconstructed")
        for i in range(0, len(rows), 500):
            await session.execute(insert(PropPick).values(rows[i : i + 500]).on_conflict_do_nothing(constraint="uq_prop_pick"))
        await session.commit()
        print(f"Reconstructed {season} week {week}: {len(rows)} picks")


async def grade(session, season: int) -> None:
    picks = (
        await session.execute(select(PropPick).where(PropPick.season == season, PropPick.result.is_(None)))
    ).scalars().all()
    if not picks:
        print("Nothing to grade.")
        return
    weeks = sorted({p.week for p in picks})
    final_teams: set[tuple[int, str]] = set()
    for g in (await session.execute(select(Game).where(Game.season == season, Game.week.in_(weeks)))).scalars():
        if g.home_score is not None and g.away_score is not None:
            final_teams |= {(g.week, g.home_team), (g.week, g.away_team)}

    stats = {
        (r.week, r.player_gsis_id): r
        for r in (
            await session.execute(
                select(PlayerGameStat).where(
                    PlayerGameStat.season == season,
                    PlayerGameStat.season_type == "REG",
                    PlayerGameStat.week.in_(weeks),
                    PlayerGameStat.player_gsis_id.in_({p.gsis_id for p in picks}),
                )
            )
        ).scalars()
    }
    now = datetime.now(timezone.utc)
    graded = voids = 0
    for p in picks:
        if (p.week, p.team) not in final_teams:
            continue
        row = stats.get((p.week, p.gsis_id))
        if row is None:
            p.result = "void"  # didn't play (or recorded no stats) -- not a miss
            voids += 1
        else:
            p.actual = float(getattr(row, STAT_COLUMN[p.stat]) or 0)
            p.result = "over" if p.actual > p.line else "under" if p.actual < p.line else "push"
        p.graded_at = now
        graded += 1
    await session.commit()
    print(f"Graded {graded} picks ({voids} void) across weeks {weeks}")


async def main() -> None:
    args = parse_args()
    async with get_sessionmaker()() as session:
        if args.reconstruct:
            lo, _, hi = args.reconstruct.partition("-")
            await reconstruct(session, args.season, list(range(int(lo), int(hi or lo) + 1)))
        if args.snapshot:
            await snapshot(session, args.season, args.week)
        if args.grade:
            await grade(session, args.season)


if __name__ == "__main__":
    asyncio.run(main())
