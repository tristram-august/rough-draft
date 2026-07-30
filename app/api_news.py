"""
NFL headlines, proxied from ESPN's undocumented public news endpoint.

This is an unofficial source with no stability guarantee, so the endpoint is
built to fail soft: a bad upstream response serves the last good payload, or an
empty list, but never a 5xx. The dashboard hides the panel when items are empty.

Proxying (rather than calling ESPN from the browser) avoids CORS, keeps the
dependency off the client, and lets one cached fetch serve every visitor.
"""
from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone

from fastapi import APIRouter, Query

from app.schemas import NewsFeedOut, NewsItemOut

router = APIRouter(tags=["news"])

ESPN_NEWS_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/news"
CACHE_TTL_SECONDS = 600
UPSTREAM_TIMEOUT_SECONDS = 8
MAX_ITEMS = 20

_cache: dict[str, object] = {"items": None, "fetched_at": None}


def _parse_published(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _fetch_espn(limit: int) -> list[NewsItemOut]:
    """Blocking fetch — call via asyncio.to_thread."""
    req = urllib.request.Request(
        f"{ESPN_NEWS_URL}?limit={limit}",
        headers={"User-Agent": "roughdraftfootball.com"},
    )
    with urllib.request.urlopen(req, timeout=UPSTREAM_TIMEOUT_SECONDS) as resp:
        payload = json.loads(resp.read())

    items: list[NewsItemOut] = []
    for article in (payload.get("articles") or [])[:limit]:
        headline = (article.get("headline") or "").strip()
        if not headline:
            continue
        links = article.get("links") or {}
        web = links.get("web") or {}
        images = article.get("images") or []
        items.append(
            NewsItemOut(
                headline=headline,
                description=(article.get("description") or "").strip() or None,
                published=_parse_published(article.get("published")),
                url=web.get("href"),
                image=images[0].get("url") if images and isinstance(images[0], dict) else None,
            )
        )
    return items


@router.get("/news", response_model=NewsFeedOut)
async def nfl_news(limit: int = Query(default=8, ge=1, le=MAX_ITEMS)) -> NewsFeedOut:
    now = datetime.now(timezone.utc)

    cached_items = _cache.get("items")
    cached_at = _cache.get("fetched_at")
    if isinstance(cached_items, list) and isinstance(cached_at, datetime):
        if (now - cached_at).total_seconds() < CACHE_TTL_SECONDS:
            return NewsFeedOut(items=cached_items[:limit], fetched_at=cached_at)

    try:
        items = await asyncio.to_thread(_fetch_espn, MAX_ITEMS)
        _cache["items"] = items
        _cache["fetched_at"] = now
        return NewsFeedOut(items=items[:limit], fetched_at=now)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError):
        # Upstream is unofficial and allowed to break. Serve whatever we last had.
        if isinstance(cached_items, list) and isinstance(cached_at, datetime):
            return NewsFeedOut(items=cached_items[:limit], fetched_at=cached_at, stale=True)
        return NewsFeedOut(items=[], fetched_at=now, stale=True)
