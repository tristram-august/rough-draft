from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_sessionmaker
from app.services.ingest_csv import ingest_csv_dir


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ingest yearly draft CSVs into Postgres.")
    p.add_argument("--csv-dir", required=True, help="Folder containing yearly CSVs (e.g. ./data/drafts).")
    return p.parse_args()


async def main() -> None:
    args = parse_args()
    csv_dir = Path(args.csv_dir).expanduser().resolve()
    if not csv_dir.exists():
        raise SystemExit(f"csv dir not found: {csv_dir}")

    session_maker = get_sessionmaker()
    async with session_maker() as session:  # type: AsyncSession
        results = await ingest_csv_dir(session, csv_dir=csv_dir)
        await session.commit()

    total = sum(results.values())
    print(f"Ingested {total} rows from {len(results)} files")
    for name, n in results.items():
        print(f"  {name}: {n}")


if __name__ == "__main__":
    asyncio.run(main())