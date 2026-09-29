"""
Rebuild Elo team ratings and per-game win predictions from scratch.

    python scripts/build_elo_ratings.py

Elo's two constants — K (how fast ratings react to a result) and home-field
advantage — aren't guessed. This grid-searches both, scoring each candidate
pair by log-loss on 2002-2019 (skipping the first three seasons as burn-in,
since every team starts flat at 1500 and ratings haven't separated enough to
be predictive yet). The winning pair is then used for one full sequential
pass over 1999-present, and everything from 2020 on is reported as a genuine
out-of-sample backtest — those seasons never influenced which K/HFA got
picked, so that accuracy number isn't fit to itself.

Also generates a prediction for every game that doesn't have a final score
yet (including all of the current season), using each team's rating as of
its most recent completed game. Rerun this after each week's games finish to
roll those results into the ratings before predicting the next week.

Both tables are truncated and rebuilt each run — there's no reason to
diff/upsert since the whole history is cheap to recompute (~7k games, a few
seconds) and it's the only way "one week's new results reshuffle everyone's
rating slightly" stays correct.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from math import log

from sqlalchemy import delete, select

from app.db import get_sessionmaker
from app.elo import GameResult, Prediction, run_elo
from app.models import EloRating, Game, GamePrediction, TeamGameStat

BURN_IN_SEASONS = 3  # seasons after the first with data, excluded from scoring
TUNE_END_SEASON = 2019  # grid search scored on [first+BURN_IN, TUNE_END_SEASON]
K_GRID = [10, 15, 20, 25, 30, 35]
HOME_FIELD_ADVANTAGE_GRID = [20, 35, 48, 55, 65, 75]
# 0.0 = today's plain score-margin Elo -- always in the grid so EPA only gets
# adopted if it actually beats that baseline on the same out-of-sample split.
EPA_SCALE_GRID = [0.0, 0.25, 0.5, 1.0, 2.0]


def _log_loss(predictions: list[Prediction], season_of: dict[str, int], lo: int, hi: int | None) -> float:
    losses = []
    for p in predictions:
        if p.home_won is None:
            continue
        season = season_of[p.game_id]
        if season < lo or (hi is not None and season > hi):
            continue
        y = 1.0 if p.home_won else 0.0
        prob = min(max(p.home_win_prob, 1e-6), 1 - 1e-6)
        losses.append(-(y * log(prob) + (1 - y) * log(1 - prob)))
    return sum(losses) / len(losses) if losses else float("inf")


def _accuracy(predictions: list[Prediction], season_of: dict[str, int], lo: int, hi: int | None) -> tuple[int, int]:
    """(correct, graded) straight-up, ties excluded like a push."""
    correct = graded = 0
    for p in predictions:
        if p.home_won is None:
            continue
        season = season_of[p.game_id]
        if season < lo or (hi is not None and season > hi):
            continue
        graded += 1
        predicted_home = p.home_win_prob >= 0.5
        if predicted_home == p.home_won:
            correct += 1
    return correct, graded


async def _load_epa_margins(session) -> dict[str, float]:
    """game_id -> (home team's total offensive EPA) - (away team's), from
    team_game_stat. A team's own passing_epa + rushing_epa this game is
    exactly what the opponent's defense allowed, so no separate "defense"
    column is needed -- see TeamGameStat's docstring."""
    rows = (
        await session.execute(
            select(TeamGameStat.game_id, TeamGameStat.team, TeamGameStat.passing_epa, TeamGameStat.rushing_epa)
        )
    ).all()
    team_epa: dict[tuple[str, str], float] = {}
    for game_id, team, passing_epa, rushing_epa in rows:
        team_epa[(game_id, team)] = (passing_epa or 0.0) + (rushing_epa or 0.0)

    home_away: dict[str, tuple[str, str]] = {}
    game_rows = (await session.execute(select(Game.game_id, Game.home_team, Game.away_team))).all()
    for game_id, home_team, away_team in game_rows:
        home_away[game_id] = (home_team, away_team)

    margins: dict[str, float] = {}
    for game_id, (home_team, away_team) in home_away.items():
        home_epa = team_epa.get((game_id, home_team))
        away_epa = team_epa.get((game_id, away_team))
        if home_epa is not None and away_epa is not None:
            margins[game_id] = home_epa - away_epa
    return margins


async def _load_games(session) -> list[GameResult]:
    epa_margins = await _load_epa_margins(session)

    rows = (
        await session.execute(
            select(
                Game.game_id, Game.season, Game.gameday, Game.gametime,
                Game.home_team, Game.away_team, Game.home_score, Game.away_score,
            )
        )
    ).all()
    games = [
        GameResult(
            game_id=r.game_id,
            season=r.season,
            sort_key=(r.gameday or datetime.min.date(), r.gametime or "", r.game_id),
            home_team=r.home_team,
            away_team=r.away_team,
            home_score=r.home_score,
            away_score=r.away_score,
            home_epa_margin=epa_margins.get(r.game_id),
        )
        for r in rows
    ]
    games.sort(key=lambda g: (g.season, g.sort_key))
    return games


async def main() -> None:
    sm = get_sessionmaker()
    async with sm() as session:
        games = await _load_games(session)
        played = [g for g in games if g.home_score is not None]
        if not played:
            print("No completed games found — nothing to build.")
            return

        season_of = {g.game_id: g.season for g in games}
        first_season = played[0].season
        tune_lo = first_season + BURN_IN_SEASONS
        with_epa = sum(1 for g in played if g.home_epa_margin is not None)
        print(f"Loaded {len(games)} games ({len(played)} final, {with_epa} with an EPA margin), {first_season}-{played[-1].season}")
        print(f"Grid-searching K x home-field-advantage x EPA-scale on {tune_lo}-{TUNE_END_SEASON}...")

        best: tuple[float, float, float, float] | None = None
        baseline: tuple[float, float, float] | None = None  # epa_scale forced to 0, for comparison
        for k in K_GRID:
            for hfa in HOME_FIELD_ADVANTAGE_GRID:
                for epa_scale in EPA_SCALE_GRID:
                    _, preds = run_elo(games, k=k, home_field_advantage=hfa, epa_scale=epa_scale)
                    loss = _log_loss(preds, season_of, tune_lo, TUNE_END_SEASON)
                    if best is None or loss < best[0]:
                        best = (loss, k, hfa, epa_scale)
                    if epa_scale == 0.0 and (baseline is None or loss < baseline[0]):
                        baseline = (loss, k, hfa)

        tune_loss, best_k, best_hfa, best_epa_scale = best
        baseline_loss, baseline_k, baseline_hfa = baseline
        print(f"Best overall: K={best_k} HFA={best_hfa} EPA-scale={best_epa_scale} (log-loss {tune_loss:.4f} on {tune_lo}-{TUNE_END_SEASON})")
        print(f"Best with EPA-scale=0 (today's model): K={baseline_k} HFA={baseline_hfa} (log-loss {baseline_loss:.4f})")
        if best_epa_scale == 0.0:
            print("EPA margin did not improve tuning log-loss -- keeping the plain score-margin model.")
        else:
            print(f"EPA margin improved tuning log-loss by {baseline_loss - tune_loss:.4f} -- adopting EPA-scale={best_epa_scale}.")

        final_ratings, predictions = run_elo(games, k=best_k, home_field_advantage=best_hfa, epa_scale=best_epa_scale)

        holdout_lo = TUNE_END_SEASON + 1
        holdout_loss = _log_loss(predictions, season_of, holdout_lo, None)
        holdout_correct, holdout_graded = _accuracy(predictions, season_of, holdout_lo, None)
        print(
            f"Out-of-sample ({holdout_lo}+): log-loss {holdout_loss:.4f}, "
            f"{holdout_correct}/{holdout_graded} correct "
            f"({holdout_correct / holdout_graded:.1%})" if holdout_graded else "no holdout games"
        )

        # Same backtest with EPA-scale forced to 0, so the holdout comparison
        # is apples-to-apples against today's model, not just the tune split.
        _, baseline_predictions = run_elo(games, k=baseline_k, home_field_advantage=baseline_hfa, epa_scale=0.0)
        baseline_holdout_loss = _log_loss(baseline_predictions, season_of, holdout_lo, None)
        baseline_holdout_correct, baseline_holdout_graded = _accuracy(baseline_predictions, season_of, holdout_lo, None)
        if baseline_holdout_graded:
            print(
                f"  vs. plain score-margin model: log-loss {baseline_holdout_loss:.4f}, "
                f"{baseline_holdout_correct}/{baseline_holdout_graded} correct "
                f"({baseline_holdout_correct / baseline_holdout_graded:.1%})"
            )

        vegas_by_game = {
            r.game_id: r.spread_line
            for r in (await session.execute(select(Game.game_id, Game.spread_line))).all()
        }

        await session.execute(delete(GamePrediction))
        await session.execute(delete(EloRating))

        now = datetime.now(timezone.utc)
        for team, rating in final_ratings.items():
            session.add(EloRating(team=team, rating=rating, updated_at=now))

        for p in predictions:
            spread = vegas_by_game.get(p.game_id)
            # spread_line is home-perspective; positive means the home team is favored.
            vegas_favorite = None
            if spread is not None and spread != 0:
                vegas_favorite = p.home_team if spread > 0 else p.away_team

            predicted_winner = p.home_team if p.home_win_prob >= 0.5 else p.away_team
            actual_winner = None
            correct = None
            vegas_correct = None
            if p.home_won is not None:
                actual_winner = p.home_team if p.home_won else p.away_team
                correct = predicted_winner == actual_winner
                if vegas_favorite is not None:
                    vegas_correct = vegas_favorite == actual_winner

            session.add(
                GamePrediction(
                    game_id=p.game_id,
                    home_elo_pre=p.home_rating_pre,
                    away_elo_pre=p.away_rating_pre,
                    home_win_prob=p.home_win_prob,
                    predicted_winner=predicted_winner,
                    actual_winner=actual_winner,
                    correct=correct,
                    vegas_favorite=vegas_favorite,
                    vegas_correct=vegas_correct,
                )
            )

        await session.commit()
        print(f"Wrote {len(final_ratings)} team ratings and {len(predictions)} game predictions.")


if __name__ == "__main__":
    asyncio.run(main())
