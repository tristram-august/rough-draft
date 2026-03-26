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
- `GET /api/draft?year=2016&round=1`
- `GET /api/pick/2016/1`
- `GET /api/player/1`
- `GET /api/team/1?year=2016`
