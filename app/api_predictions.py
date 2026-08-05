"""
Backtested accuracy of the Elo prediction model — see app/elo.py for the
model itself and scripts/build_elo_ratings.py for how it's built. Per-game
predictions are exposed through the picks slate (app/api_picks.py), not
here; this is just the public track-record number.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import db_session
from app.models import Game, GamePrediction
from app.schemas import PredictionAccuracyOut

router = APIRouter(tags=["predictions"])

# Must match scripts/build_elo_ratings.py's TUNE_END_SEASON + 1: everything
# from this season on was never used to pick the model's K / home-field
# constants, so it's a genuine out-of-sample backtest rather than a number
# fit to itself.
HOLDOUT_START_SEASON = 2020


@router.get("/predictions/accuracy", response_model=PredictionAccuracyOut)
async def prediction_accuracy(session: AsyncSession = Depends(db_session)) -> PredictionAccuracyOut:
    row = (
        await session.execute(
            select(
                func.count().filter(GamePrediction.correct.is_(True)),
                func.count().filter(GamePrediction.correct.is_not(None)),
                func.count().filter(GamePrediction.vegas_correct.is_(True)),
                func.count().filter(GamePrediction.vegas_correct.is_not(None)),
                func.max(Game.season).filter(GamePrediction.correct.is_not(None)),
            )
            .select_from(GamePrediction)
            .join(Game, Game.game_id == GamePrediction.game_id)
            .where(Game.season >= HOLDOUT_START_SEASON)
        )
    ).one()
    model_correct, model_graded, vegas_correct, vegas_graded, season_to = row

    return PredictionAccuracyOut(
        season_from=HOLDOUT_START_SEASON,
        season_to=season_to or HOLDOUT_START_SEASON,
        model_correct=model_correct or 0,
        model_graded=model_graded or 0,
        vegas_correct=vegas_correct or 0,
        vegas_graded=vegas_graded or 0,
    )
