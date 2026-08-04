"""
NFL headlines, blended from public RSS feeds and proxied to the frontend.

Originally this called ESPN's undocumented internal news API
(site.api.espn.com/.../news), but that endpoint is meant for ESPN's own app,
not public consumption — Akamai started 403-ing most requests to it. RSS feeds
are the opposite: outlets publish them specifically to be scraped by third
parties, so they're a sturdier long-term source. ESPN's own public RSS feed
(espn.com/espn/rss/nfl/news) has been reliable in testing, and we blend in
Pro Football Talk's feed too, both for more headlines and so one outlet
having a bad day doesn't empty the whole widget.

This is still an unofficial, best-effort feature: it's built to fail soft (a
bad upstream response serves the last good payload, or an empty list, but
never a 5xx), and the dashboard hides the panel when items are empty.

Proxying (rather than fetching from the browser) avoids CORS, keeps the
dependency off the client, and lets one cached fetch serve every visitor.

The last-good payload is also persisted to `news_cache` in Postgres (see
NewsCache in app/models.py), not just held in memory, so a redeploy landing
mid-outage still has yesterday's headlines to serve instead of nothing while
it keeps retrying.
"""
from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import db_session
from app.models import NewsCache
from app.schemas import NewsFeedOut, NewsItemOut

router = APIRouter(tags=["news"])

RSS_SOURCES: list[tuple[str, str]] = [
    ("ESPN", "https://www.espn.com/espn/rss/nfl/news"),
    ("PFT", "https://www.nbcsports.com/profootballtalk.rss"),
]
CACHE_TTL_SECONDS = 600
UPSTREAM_TIMEOUT_SECONDS = 8
MAX_ITEMS = 20
CACHE_ROW_ID = 1

_cache: dict[str, object] = {"items": None, "fetched_at": None}


async def _load_db_cache(session: AsyncSession) -> tuple[list[NewsItemOut], datetime] | None:
    row = await session.get(NewsCache, CACHE_ROW_ID)
    if row is None:
        return None
    items = [NewsItemOut(**d) for d in json.loads(row.items_json)]
    return items, row.fetched_at


async def _save_db_cache(session: AsyncSession, items: list[NewsItemOut], fetched_at: datetime) -> None:
    payload = json.dumps([item.model_dump(mode="json") for item in items])
    stmt = insert(NewsCache).values(id=CACHE_ROW_ID, items_json=payload, fetched_at=fetched_at)
    stmt = stmt.on_conflict_do_update(
        index_elements=["id"],
        set_={"items_json": stmt.excluded.items_json, "fetched_at": stmt.excluded.fetched_at},
    )
    await session.execute(stmt)
    await session.commit()


def _parse_rss_pubdate(raw: str | None) -> datetime | None:
    """RSS pubDate is RFC 822-ish ("Tue, 4 Aug 2026 15:12:37 EST" or "... -0400");
    email.utils understands both the named US zone abbreviations and numeric
    offsets, which is why this reuses it instead of a hand-rolled format."""
    if not raw:
        return None
    try:
        dt = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _fetch_rss(source: str, url: str, limit: int) -> list[NewsItemOut]:
    """Blocking fetch of one RSS 2.0 feed — call via asyncio.to_thread."""
    req = urllib.request.Request(url, headers={"User-Agent": "roughdraftfootball.com"})
    with urllib.request.urlopen(req, timeout=UPSTREAM_TIMEOUT_SECONDS) as resp:
        root = ET.fromstring(resp.read())

    items: list[NewsItemOut] = []
    for entry in root.findall("./channel/item")[:limit]:
        headline = (entry.findtext("title") or "").strip()
        if not headline:
            continue
        items.append(
            NewsItemOut(
                headline=headline,
                description=(entry.findtext("description") or "").strip() or None,
                published=_parse_rss_pubdate(entry.findtext("pubDate")),
                url=(entry.findtext("link") or "").strip() or None,
                image=None,
                source=source,
            )
        )
    return items


def _fetch_all(limit: int) -> list[NewsItemOut]:
    """Blocking fetch of every configured source, merged newest-first. Call via
    asyncio.to_thread. One source failing doesn't sink the others — only raises
    if every source fails, since that's the case with nothing worth serving."""
    items: list[NewsItemOut] = []
    failures = 0
    for source, url in RSS_SOURCES:
        try:
            items.extend(_fetch_rss(source, url, limit))
        except (urllib.error.URLError, TimeoutError, ET.ParseError, OSError, ValueError):
            failures += 1
    if failures == len(RSS_SOURCES):
        raise ValueError("all news sources failed")
    epoch = datetime.min.replace(tzinfo=timezone.utc)
    items.sort(key=lambda item: item.published or epoch, reverse=True)
    return items


@router.get("/news", response_model=NewsFeedOut)
async def nfl_news(
    limit: int = Query(default=8, ge=1, le=MAX_ITEMS),
    session: AsyncSession = Depends(db_session),
) -> NewsFeedOut:
    now = datetime.now(timezone.utc)

    cached_items = _cache.get("items")
    cached_at = _cache.get("fetched_at")

    # A fresh process (post-deploy) starts with an empty in-memory cache even
    # though ESPN may have been fine an hour ago — check the DB before
    # deciding there's nothing to serve.
    if not isinstance(cached_items, list) or not isinstance(cached_at, datetime):
        db_hit = await _load_db_cache(session)
        if db_hit is not None:
            cached_items, cached_at = db_hit
            _cache["items"] = cached_items
            _cache["fetched_at"] = cached_at

    if isinstance(cached_items, list) and isinstance(cached_at, datetime):
        if (now - cached_at).total_seconds() < CACHE_TTL_SECONDS:
            return NewsFeedOut(items=cached_items[:limit], fetched_at=cached_at)

    try:
        items = await asyncio.to_thread(_fetch_all, MAX_ITEMS)
        if items:
            # A "success" with zero items is itself worth distrusting — don't
            # let it clobber a good fallback in the DB.
            _cache["items"] = items
            _cache["fetched_at"] = now
            await _save_db_cache(session, items, now)
            return NewsFeedOut(items=items[:limit], fetched_at=now)
        raise ValueError("every news source returned zero items")
    except (urllib.error.URLError, TimeoutError, ET.ParseError, OSError, ValueError):
        # Upstream sources are unofficial and allowed to break. Serve whatever
        # we last had, in memory or (after a restart) from the DB, however old.
        if isinstance(cached_items, list) and isinstance(cached_at, datetime):
            return NewsFeedOut(items=cached_items[:limit], fetched_at=cached_at, stale=True)
        return NewsFeedOut(items=[], fetched_at=now, stale=True)
