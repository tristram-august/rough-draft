"""
Shared HTTP client for the FantasyPros public API, used by every ingest
script (scripts/ingest_fantasypros*.py) and by the live /players/compare
endpoint. Extracted from scripts/ingest_fantasypros.py so there's one
implementation of auth/rate-limit/error-handling, not four copies.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from app.settings import settings

API_BASE = "https://api.fantasypros.com/public/v2/json/nfl"
RATE_LIMIT_SECONDS = 1.1  # premium plan is 1 req/sec; leave a little headroom


def fetch(path: str, params: dict) -> dict:
    if not settings.fantasypros_api_key:
        raise SystemExit("FANTASYPROS_API_KEY is not set (see .env / app/settings.py)")
    qs = urllib.parse.urlencode(params)
    url = f"{API_BASE}{path}?{qs}" if qs else f"{API_BASE}{path}"
    req = urllib.request.Request(url, headers={"x-api-key": settings.fantasypros_api_key})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"FantasyPros API error {e.code} on {path}: {body}") from e


def warn_if_capped(resp: dict) -> None:
    if resp.get("public_api_limited") and resp.get("limit"):
        print(f"  WARNING: response capped at {resp['limit']} rows (tier={resp.get('tier')}) — "
              f"got {len(resp.get('players', []))} of {resp.get('count')}")
