# Deployment Guide

## Environment Variables

Set these in your hosting platform (never commit them):

| Variable | Required | Description | Example |
|---|---|---|---|
| `DATABASE_URL` | ✅ | Async postgres connection string | `postgresql+asyncpg://user:pass@host:5432/db` |
| `SECRET_KEY` | ✅ | JWT signing secret — long random string | `openssl rand -hex 32` |
| `APP_ENV` | ✅ | Must be `production` to enable startup guard | `production` |
| `CORS_ORIGINS` | ✅ | Comma-separated allowed origins | `https://yourdomain.com` |
| `VOTING_LOCK_FROM_YEAR` | ✗ | First draft year with voting disabled (default: 2026) | `2027` |
| `APP_DEBUG` | ✗ | Enable debug mode (default: false) | `false` |
| `SMTP_HOST` | ✗ | SMTP server hostname — leave empty to disable email (logs links to console instead) | `smtp.sendgrid.net` |
| `SMTP_PORT` | ✗ | SMTP port (default: 587) | `587` |
| `SMTP_USER` | ✗ | SMTP username | `apikey` |
| `SMTP_PASSWORD` | ✗ | SMTP password / API key | `SG.xxxxx` |
| `SMTP_FROM` | ✗ | From address for outgoing emails | `noreply@yourdomain.com` |
| `APP_URL` | ✗ | Public frontend URL used in email links (default: http://localhost:3000) | `https://yourdomain.com` |

> The app will **refuse to start** if `APP_ENV=production` and `SECRET_KEY` is still the default.

---

## First-Time Production Setup

```bash
# 1. Run all database migrations
docker exec <api-container> alembic upgrade head

# 2. Ingest draft pick CSVs (all years)
docker exec <api-container> python3 scripts/ingest_csvs.py --csv-dir data/drafts/

# 3. Ingest player dimension data (headshots, bio, GSIS IDs)
docker exec <api-container> python3 scripts/ingest_players_nfl.py

# 4. Ingest game stats (one file per season, 2000+)
docker exec <api-container> python3 scripts/ingest_player_stats_subset.py

# 5. Ingest OL blocking stats (one year at a time)
docker exec <api-container> python3 scripts/ingest_ol_stats.py data/ol_stats/offense_blocking_2025.csv --season 2025
# repeat for each year 2006–2025
```

---

## Each New Draft Year

```bash
# 1. Add draft_picks_YYYY.csv to data/drafts/ then ingest
docker exec <api-container> python3 scripts/ingest_csvs.py --csv-dir data/drafts/

# 2. Update voting lock year in env (new class can't be voted on yet)
VOTING_LOCK_FROM_YEAR=2027   # set in your hosting platform

# 3. When ready to open voting for the previous year's class
VOTING_LOCK_FROM_YEAR=2027   # leave as-is until they've played a full season
# then bump to 2028 after their rookie year ends

# 4. Add OL stats when PFF data is available
docker exec <api-container> python3 scripts/ingest_ol_stats.py data/ol_stats/offense_blocking_YYYY.csv --season YYYY
```

> OL stats only go back to 2006 — players drafted before then will show "data starts 2006" in the drawer.

> The year dropdown in the UI is hardcoded — bump the array length in `frontend/rough-draft-ui/app/ui/draft-board-page.tsx` (search for `Array.from({ length:`) each new draft year.

---

## Granting Mod Access

Mods can delete any comment. Grant via direct DB update:

```sql
UPDATE "user" SET is_mod = true WHERE username = 'username-here';
```

```bash
# Via docker
docker exec <db-container> psql -U <db-user> -d <db-name> -c "UPDATE \"user\" SET is_mod = true WHERE username = 'username-here';"
```

The user must **log out and back in** after being granted mod — the flag is encoded in the JWT at login time.

---

## Database Migrations

```bash
# Apply all pending migrations
docker exec <api-container> alembic upgrade head

# Check current migration state
docker exec <api-container> alembic current

# Migration history
docker exec <api-container> alembic history
```

Migrations live in `app/alembic/versions/` and run in order:
- `0001` — initial schema
- `0002` — votes
- `0003` — career summaries
- `0004` — users + comments
- `0005` — OL season stats
- `0006` — mod flag on user
- `0007` — email verification + password reset tokens

---

## Generating a SECRET_KEY

```bash
# Linux/Mac
openssl rand -hex 32

# PowerShell
[System.Convert]::ToBase64String((1..32 | ForEach-Object { [byte](Get-Random -Max 256) }))
```

---

## Local Dev Quick Start

```bash
# Start API + DB
docker compose up -d

# Start frontend
cd frontend/rough-draft-ui && npm run dev

# API:      http://localhost:8000
# Frontend: http://localhost:3000
# API docs: http://localhost:8000/docs
```

---

## Rate Limits

- `POST /api/auth/register` — 5 requests/minute per IP
- `POST /api/auth/login` — 10 requests/minute per IP
- All other endpoints — unlimited (add `@limiter.limit(...)` in `app/api.py` as needed)
