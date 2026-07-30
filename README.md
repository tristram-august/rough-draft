# NFL Draft Board API (FastAPI)

## Quickstart (Docker)
1) `docker compose up --build`
2) In another terminal:
   - `docker compose exec api alembic upgrade head`
3) Open:
   - http://localhost:8000/docs
   - http://localhost:8000/api/health

## Demo ingest (optional)
- `docker compose exec api python scripts/run_ingest_demo.py`

## Example calls

### Draft board
- `GET /api/draft?year=2016&round=1`
- `GET /api/pick/2016/1`
- `GET /api/player/1`
- `GET /api/team/1?year=2016`

### Fantasy
- `GET /api/fantasy/seasons`
- `GET /api/fantasy/weeks?season=2024`
- `GET /api/fantasy/leaderboard?season=2024&position=RB&scoring=ppr&sort=ppg`
- `GET /api/fantasy/player/{gsis_id}?scoring=half&season=2024`

Scoring presets: `ppr` (1/reception), `half` (0.5), `std` (0). Everything else is
shared: 1 pt per 25 passing yards, 4 per passing TD, −2 per interception, 1 pt per
10 rushing/receiving yards, 6 per rushing/receiving TD, −2 per fumble lost.

### Schedule & news (dashboard)
- `GET /api/schedule/upcoming?limit=16` — next slate, with an offseason countdown
- `GET /api/schedule/week?season=2026&week=1`
- `GET /api/schedule/seasons`
- `GET /api/news?limit=8` — NFL headlines

Schedules come from the nflverse `games.csv` feed and share `game_id` with
`player_game_stat`, so they join directly. Ingest with:

```
docker compose exec api python scripts/ingest_schedules.py
```

nflverse uses `LA` for the Rams where this repo uses `LAR`; the ingest aliases
that (plus `OAK`→`LV`, `SD`→`LAC`, `STL`→`LAR`) so games join to `team`.

`/api/news` proxies ESPN's **undocumented** public news endpoint, cached for 10
minutes. It has no stability guarantee, so it fails soft: on an upstream error it
serves the last good payload (`stale: true`) or an empty list — never a 5xx. The
dashboard hides the panel when `items` is empty.

### Blog
- `GET /api/posts?tag=fantasy&limit=20`
- `GET /api/posts/tags`
- `GET /api/posts/{slug}`
- `POST /api/posts` — mod only
- `PUT /api/posts/{post_id}` — mod only
- `DELETE /api/posts/{post_id}` — mod only

Drafts are only visible to mods: pass a mod bearer token plus
`include_drafts=true` on the list endpoint, or request the slug directly.
