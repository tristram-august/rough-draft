from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api import router
from app.api_blog import router as blog_router
from app.api_fantasy import router as fantasy_router
from app.api_matchup_stats import router as matchup_stats_router
from app.api_mock_draft import router as mock_draft_router
from app.api_news import router as news_router
from app.api_picks import router as picks_router
from app.api_predictions import router as predictions_router
from app.api_power import router as power_router
from app.api_schedule import router as schedule_router
from app.limiter import limiter
from app.settings import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title="NFL Draft Board API",
        version="0.1.0",
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix="/api")
    app.include_router(blog_router, prefix="/api")
    app.include_router(fantasy_router, prefix="/api")
    app.include_router(schedule_router, prefix="/api")
    app.include_router(picks_router, prefix="/api")
    app.include_router(power_router, prefix="/api")
    app.include_router(mock_draft_router, prefix="/api")
    app.include_router(matchup_stats_router, prefix="/api")
    app.include_router(news_router, prefix="/api")
    app.include_router(predictions_router, prefix="/api")
    return app
