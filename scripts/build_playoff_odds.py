"""
Build weekly playoff odds (playoff_odds) and the model's backtest (playoff_calibration).

    python -m scripts.build_playoff_odds                   # current season, every week so far
    python -m scripts.build_playoff_odds --backtest        # also re-score 2020 through last season

Run after scripts/build_elo_ratings.py each week. A snapshot "as of week N"
fixes every final game through week N and simulates the rest using each
team's Elo rating at that point (the pre-game rating of its next game), so
re-running never leaks later results into earlier weeks.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone

from sqlalchemy import delete, func, select

from app.db import get_sessionmaker
from app.models import Game, GamePrediction, PlayoffCalibration, PlayoffOdds, Team
from app.playoffs import RATING_SD, SeasonGame, implied_home_field_advantage, simulate_season

BACKTEST_FROM = 2020  # Elo's K/HFA were tuned on 2002-2019, so 2020+ is out of sample
TUNE_FROM = 2010  # rating noise is tuned on 2010-2019, inside Elo's own tuning window
SD_GRID = [0, 50, 100, 125, 150, 175, 200]
TUNE_SIMS = 1_000
BUCKETS = [0.0, 0.05, 0.15, 0.3, 0.5, 0.7, 0.85, 0.95, 1.0000001]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--season", type=int, default=None, help="Defaults to the latest season on the schedule.")
    p.add_argument("--sims", type=int, default=10_000)
    p.add_argument("--backtest", action="store_true")
    p.add_argument("--backtest-sims", type=int, default=2_000)
    return p.parse_args()


async def load_season(session, season: int):
    rows = (
        await session.execute(
            select(Game, GamePrediction)
            .join(GamePrediction, GamePrediction.game_id == Game.game_id)
            .where(Game.season == season)
            .order_by(Game.week, Game.gameday, Game.gametime, Game.game_id)
        )
    ).all()
    reg = [
        SeasonGame(g.week, g.home_team, g.away_team, g.home_score, g.away_score, p.home_elo_pre, p.away_elo_pre)
        for g, p in rows
        if g.game_type == "REG"
    ]
    post_teams = {t for g, _ in rows if g.game_type != "REG" for t in (g.home_team, g.away_team)}
    # Each team's games in order, for "rating as of week N" lookups (POST included).
    by_team: dict[str, list[tuple[int, bool, float]]] = {}
    for g, p in rows:
        final = g.home_score is not None and g.away_score is not None
        by_team.setdefault(g.home_team, []).append((g.week, final, p.home_elo_pre))
        by_team.setdefault(g.away_team, []).append((g.week, final, p.away_elo_pre))
    hfa = implied_home_field_advantage(reg, [p.home_win_prob for g, p in rows if g.game_type == "REG"])
    return reg, post_teams, by_team, hfa


def ratings_as_of(by_team: dict[str, list[tuple[int, bool, float]]], week: int) -> dict[str, float]:
    """Pre-game rating of each team's first game after `week` (or first unplayed
    game) -- i.e. its rating once everything through `week` was known."""
    out = {}
    for team, games in by_team.items():
        nxt = next((pre for w, final, pre in games if w > week or not final), None)
        out[team] = nxt if nxt is not None else games[-1][2]
    return out


async def build_current(session, teams, season: int, sims: int) -> None:
    reg, _, by_team, hfa = await load_season(session, season)
    final_weeks = [g.week for g in reg if g.final]
    last_week = max(final_weeks) if final_weeks else 0
    now = datetime.now(timezone.utc)
    await session.execute(delete(PlayoffOdds).where(PlayoffOdds.season == season))
    for week in range(0, last_week + 1):
        odds = simulate_season(reg, teams, ratings_as_of(by_team, week), hfa, week, sims=sims, seed=season * 100 + week)
        session.add_all(
            PlayoffOdds(
                season=season, week=week, team=o.team, elo=o.elo, wins=o.wins, losses=o.losses,
                mean_wins=o.mean_wins, make_playoffs=o.make_playoffs, win_division=o.win_division,
                first_seed=o.first_seed, win_conference=o.win_conference, win_super_bowl=o.win_super_bowl,
                seed_probs=json.dumps([round(x, 4) for x in o.seed_probs]), sims=sims, updated_at=now,
            )
            for o in odds
        )
        top = sorted(odds, key=lambda o: -o.win_super_bowl)[:3]
        print(f"{season} week {week:>2}: favorites {', '.join(f'{o.team} {o.win_super_bowl:.0%}' for o in top)}")
    await session.commit()
    print(f"HFA used: {hfa:.1f} Elo points")


def season_predictions(data, teams, season: int, sd: float, sims: int) -> list[tuple[float, bool]]:
    reg, post_teams, by_team, hfa = data
    last_reg_week = max(g.week for g in reg)
    out = []
    for week in range(0, last_reg_week):  # the final week is all known results -- nothing to predict
        odds = simulate_season(
            reg, teams, ratings_as_of(by_team, week), hfa, week, sims=sims, seed=season * 100 + week,
            rating_sd=sd, wildcards=3 if season >= 2020 else 2,
        )
        out.extend((o.make_playoffs, o.team in post_teams) for o in odds)
    return out


def brier(preds: list[tuple[float, bool]]) -> float:
    return sum((p - a) ** 2 for p, a in preds) / len(preds)


async def build_backtest(session, teams, through: int, sims: int) -> None:
    cache = {}
    for season in range(TUNE_FROM, through + 1):
        data = await load_season(session, season)
        if data[1]:
            cache[season] = data

    tune_seasons = [s for s in cache if s < BACKTEST_FROM]
    scores = {}
    for sd in SD_GRID:
        preds = [p for s in tune_seasons for p in season_predictions(cache[s], teams, s, sd, TUNE_SIMS)]
        scores[sd] = brier(preds)
        print(f"tune rating_sd={sd:>3}: Brier {scores[sd]:.4f} ({TUNE_FROM}-{BACKTEST_FROM - 1})")
    best_sd = min(scores, key=scores.get)
    print(f"Best rating_sd on {TUNE_FROM}-{BACKTEST_FROM - 1}: {best_sd}  (app.playoffs.RATING_SD is {RATING_SD})")

    test_seasons = [s for s in cache if s >= BACKTEST_FROM]
    baseline = [p for s in test_seasons for p in season_predictions(cache[s], teams, s, 0.0, sims)]
    preds = [p for s in test_seasons for p in season_predictions(cache[s], teams, s, best_sd, sims)]
    print(f"Out of sample {BACKTEST_FROM}-{through}: Brier {brier(preds):.4f} with rating_sd={best_sd}, "
          f"{brier(baseline):.4f} frozen (always guessing 14/32 would score ~0.246), {len(preds)} team-weeks")
    now = datetime.now(timezone.utc)
    await session.execute(delete(PlayoffCalibration))
    for lo, hi in zip(BUCKETS, BUCKETS[1:]):
        bucket = [(p, a) for p, a in preds if lo <= p < hi]
        if not bucket:
            continue
        predicted = sum(p for p, _ in bucket) / len(bucket)
        actual = sum(a for _, a in bucket) / len(bucket)
        print(f"  {lo:>4.0%}-{min(hi, 1):>4.0%}: n={len(bucket):>5}  predicted {predicted:6.1%}  actual {actual:6.1%}")
        session.add(PlayoffCalibration(
            bucket_lo=lo, bucket_hi=min(hi, 1.0), n=len(bucket), predicted=predicted, actual=actual,
            seasons=f"{BACKTEST_FROM}-{through}", updated_at=now,
        ))
    await session.commit()


async def main() -> None:
    args = parse_args()
    async with get_sessionmaker()() as session:
        teams = {r.abbrev: (r.conference, r.division) for r in (await session.execute(select(Team))).scalars()}
        season = args.season or (await session.execute(select(func.max(Game.season)).where(Game.game_type == "REG"))).scalar()
        await build_current(session, teams, season, args.sims)
        if args.backtest:
            await build_backtest(session, teams, season - 1, args.backtest_sims)


if __name__ == "__main__":
    asyncio.run(main())
