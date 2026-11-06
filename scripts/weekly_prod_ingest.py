"""
Run the weekly production ingest: the 8 docker-compose commands, in order,
against Railway's Postgres.

    python scripts/weekly_prod_ingest.py --week 9               # print the plan only
    python scripts/weekly_prod_ingest.py --week 9 --yes         # actually run it
    python scripts/weekly_prod_ingest.py --week 9 --yes --from-step 5   # resume after a failure

--week is the UPCOMING week (what ingest_fantasypros_projections --week wants);
scripts/download_weekly_stats.py reports it as upcoming_week.

Runs on the host (stdlib only), not in the container. The production URL is
read at run time from the Railway CLI (Postgres service's DATABASE_PUBLIC_URL,
in the linked project) and handed to `docker compose exec -e DATABASE_URL`
by name through the environment, so it never appears on a command line, in
output, or on disk. Requires: `railway` CLI logged in + linked, and the local
api container running (`docker compose up -d api`).

Without --yes nothing touches production. Stops at the first failing step and
prints the --from-step to resume from.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RAILWAY_DB_SERVICE = "Postgres"


def steps(season: int, week: int) -> list[tuple[str, list[str]]]:
    py = ["python", "-m"]
    return [
        ("Player stats", py + ["scripts.ingest_player_stats_subset", "--csv-dir", "./data/player_stats",
                               "--from-year", str(season), "--to-year", str(season)]),
        ("FantasyPros projections", py + ["scripts.ingest_fantasypros_projections",
                                          "--season", str(season), "--week", str(week)]),
        ("Team stats", py + ["scripts.ingest_team_stats", "--from-year", str(season), "--to-year", str(season)]),
        ("Schedules", py + ["scripts.ingest_schedules", "--from-year", str(season), "--to-year", str(season)]),
        ("Elo ratings", py + ["scripts.build_elo_ratings"]),
        ("Playoff odds", py + ["scripts.build_playoff_odds", "--backtest"]),
        ("Refresh weekly", py + ["scripts.refresh_weekly"]),
        ("Prop scorecard", py + ["scripts.prop_scorecard", "--reconstruct", "1-6", "--snapshot", "--grade"]),
    ]


def prod_database_url() -> str:
    exe = shutil.which("railway.cmd") or shutil.which("railway")
    if not exe:
        raise SystemExit("railway CLI not found on PATH.")
    r = subprocess.run([exe, "variables", "--service", RAILWAY_DB_SERVICE, "--json"],
                       capture_output=True, text=True, cwd=REPO_ROOT)
    if r.returncode:
        raise SystemExit(f"railway variables failed (logged in? project linked?): {r.stderr.strip()[:300]}")
    url = json.loads(r.stdout).get("DATABASE_PUBLIC_URL")
    if not url:
        raise SystemExit(f"No DATABASE_PUBLIC_URL on Railway service {RAILWAY_DB_SERVICE!r}.")
    # The app needs SQLAlchemy's async driver scheme.
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            url = "postgresql+asyncpg://" + url[len(prefix):]
    return url


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--week", type=int, required=True, help="Upcoming week (projections week).")
    p.add_argument("--season", type=int, default=2026)
    p.add_argument("--from-step", type=int, default=1, help="1-based step to start from (resume).")
    p.add_argument("--yes", action="store_true", help="Actually run against production.")
    args = p.parse_args()

    plan = steps(args.season, args.week)
    print(f"Weekly production ingest -- season {args.season}, projections week {args.week}")
    for i, (name, cmd) in enumerate(plan, 1):
        mark = "skip" if i < args.from_step else "    "
        print(f"  {mark} {i}. {name:<24} {' '.join(cmd)}")

    if not args.yes:
        print("\nPlan only -- nothing was run. Add --yes to run against production.")
        return

    env = {**os.environ, "DATABASE_URL": prod_database_url()}
    print(f"\nUsing Railway service {RAILWAY_DB_SERVICE!r} DATABASE_PUBLIC_URL (not printed).")

    for i, (name, cmd) in enumerate(plan, 1):
        if i < args.from_step:
            continue
        print(f"\n=== [{i}/{len(plan)}] {name} ===", flush=True)
        t0 = time.monotonic()
        rc = subprocess.run(["docker", "compose", "exec", "-T", "-e", "DATABASE_URL", "api", *cmd],
                            env=env, cwd=REPO_ROOT).returncode
        dt = time.monotonic() - t0
        if rc:
            print(f"\nFAILED: step {i} ({name}) exited {rc} after {dt:.0f}s.")
            print(f"Fix it, then resume with: --week {args.week} --yes --from-step {i}")
            sys.exit(rc)
        print(f"--- {name} OK ({dt:.0f}s)")

    print(f"\nAll {len(plan)} steps finished.")


if __name__ == "__main__":
    main()
