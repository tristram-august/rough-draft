"""
NFL team Elo ratings and win-probability predictions.

Standard sequential Elo: every team starts at 1500, and a rating updates
after each *final* game based on the gap between the actual result and the
pre-game win probability, scaled by a margin-of-victory multiplier (a
one-point win shouldn't move a rating as much as a blowout) — the same
family of model 538 popularized for NFL Elo. K (how fast ratings react) and
home-field advantage aren't guessed here; scripts/build_elo_ratings.py
grid-searches both against real history and reports genuine out-of-sample
accuracy for whatever it picks.

Games without a final score (postponed, or not yet played) still get a
prediction from each team's *current* pre-game rating, but don't feed back
into anyone's rating — there's no result yet to learn from.

Ratings persist across a team's whole history; only a partial reversion
toward 1500 happens at the first game of a new season, since rosters turn
over enough that last year's rating shouldn't be fully "sticky," but a full
reset would throw away everything the model knows about a stable team.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import log
from typing import Iterable, NamedTuple

START_RATING = 1500.0
SEASON_REVERSION = 1 / 3  # fraction of the gap back to 1500 applied at a team's first game of a new season


class GameResult(NamedTuple):
    game_id: str
    season: int
    sort_key: tuple  # (gameday, gametime, game_id) — chronological tiebreak within a season
    home_team: str
    away_team: str
    home_score: int | None
    away_score: int | None
    # home team's total offensive EPA (passing + rushing) minus away's, this
    # game -- from team_game_stat, via build_elo_ratings.py. None when that
    # data isn't available for the game (pre-1999, or not yet ingested).
    home_epa_margin: float | None = None


@dataclass
class Prediction:
    game_id: str
    home_team: str
    away_team: str
    home_rating_pre: float
    away_rating_pre: float
    home_win_prob: float
    home_won: bool | None  # None: tie, or game not yet final


def win_probability(home_rating: float, away_rating: float, home_field_advantage: float) -> float:
    diff = (home_rating + home_field_advantage) - away_rating
    return 1.0 / (1.0 + 10 ** (-diff / 400.0))


def _mov_multiplier(margin: int, elo_diff_winner: float) -> float:
    """538's margin-of-victory dampener: a bigger margin moves ratings more,
    but the effect tapers as the winner's pre-game expected margin grows —
    a 40-point win by a team already miles ahead shouldn't move it much
    further, since that result was already expected."""
    return log(max(margin, 1) + 1) * (2.2 / (0.001 * elo_diff_winner + 2.2))


def run_elo(
    games: Iterable[GameResult], k: float, home_field_advantage: float, epa_scale: float = 0.0
) -> tuple[dict[str, float], list[Prediction]]:
    """Processes games in the order given, which must already be chronological
    (season, then date within season). Returns each team's rating as of the
    last game in the list, and one Prediction per game.

    epa_scale (default 0, i.e. today's plain score-margin Elo, unchanged)
    blends each game's EPA margin into the point margin the MOV multiplier
    sees, from the *winner's* perspective: a win where the winner also
    outgained the loser on EPA gets amplified, a "lucky" win where the loser
    actually out-EPA'd the winner gets dampened. scripts/build_elo_ratings.py
    grid-searches this alongside K/HFA and only keeps it if it actually beats
    epa_scale=0 on the same out-of-sample backtest."""
    ratings: dict[str, float] = {}
    season_seen: dict[str, int] = {}
    predictions: list[Prediction] = []

    def rating_for(team: str, season: int) -> float:
        current = ratings.get(team, START_RATING)
        last_season = season_seen.get(team)
        if last_season is not None and last_season != season:
            current = current + (START_RATING - current) * SEASON_REVERSION
        season_seen[team] = season
        ratings[team] = current
        return current

    for g in games:
        home_pre = rating_for(g.home_team, g.season)
        away_pre = rating_for(g.away_team, g.season)
        prob_home = win_probability(home_pre, away_pre, home_field_advantage)

        if g.home_score is None or g.away_score is None or g.home_score == g.away_score:
            predictions.append(
                Prediction(
                    game_id=g.game_id,
                    home_team=g.home_team,
                    away_team=g.away_team,
                    home_rating_pre=home_pre,
                    away_rating_pre=away_pre,
                    home_win_prob=prob_home,
                    home_won=None,
                )
            )
            continue

        home_won = g.home_score > g.away_score
        actual = 1.0 if home_won else 0.0
        margin = abs(g.home_score - g.away_score)
        winner_diff = (
            (home_pre + home_field_advantage) - away_pre
            if home_won
            else away_pre - (home_pre + home_field_advantage)
        )

        effective_margin = margin
        if epa_scale and g.home_epa_margin is not None:
            epa_margin_for_winner = g.home_epa_margin if home_won else -g.home_epa_margin
            effective_margin = max(margin + epa_scale * epa_margin_for_winner, 0.0)

        k_eff = k * _mov_multiplier(effective_margin, max(winner_diff, 0.0))
        delta = k_eff * (actual - prob_home)

        ratings[g.home_team] = home_pre + delta
        ratings[g.away_team] = away_pre - delta

        predictions.append(
            Prediction(
                game_id=g.game_id,
                home_team=g.home_team,
                away_team=g.away_team,
                home_rating_pre=home_pre,
                away_rating_pre=away_pre,
                home_win_prob=prob_home,
                home_won=home_won,
            )
        )

    return ratings, predictions
