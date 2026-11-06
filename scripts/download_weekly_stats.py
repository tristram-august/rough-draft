"""
Download the just-finished week's player stats from nflverse (via nflreadpy)
into data/player_stats/player_stats_{season}_week{N}.csv, and report which
week finished / which week is up next, for the weekly production ingest.

    python -m scripts.download_weekly_stats              # auto-detect weeks
    python -m scripts.download_weekly_stats --week 8     # force the stats week
    python -m scripts.download_weekly_stats --dry-run    # detect + report only

The last line of output is a JSON summary (season, completed_week,
upcoming_week, csv, rows, unfinished_games) so a wrapper can pick the weeks up
without hand-entering them. upcoming_week is what
ingest_fantasypros_projections --week wants.

Only player stats need a local CSV: ingest_schedules and ingest_team_stats
fetch from nflverse themselves when run without --csv/--csv-dir.

nflreadpy is deliberately not a project dependency (production never needs
it). Run this inside the local api container, where the network/SSL works:
    docker compose exec api pip install nflreadpy
    docker compose exec api python -m scripts.download_weekly_stats
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import nflreadpy as nfl
import polars as pl

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "data" / "player_stats"
MIN_EXPECTED_ROWS = 500  # a full regular-season week is ~950-1000 player rows


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--season", type=int, default=None, help="Defaults to nflreadpy's current season.")
    p.add_argument("--week", type=int, default=None, help="Stats week to download (defaults to the latest completed week).")
    p.add_argument("--dry-run", action="store_true", help="Detect weeks and report, but don't download stats.")
    return p.parse_args()


def detect_weeks(season: int) -> dict:
    """Upcoming week = earliest week with a game still unscored; completed
    week = the one before it. Scores, not dates, so a Tuesday run after MNF
    reports (8, 9).

    Two warnings, both in the summary rather than silently shifting weeks:
      - already_final_in_upcoming: run mid-week (after TNF) -- the upcoming
        week has started, so its projections/snapshot may be late.
      - unfinished_games: unscored games in a week *before* the latest
        played one, i.e. a postponement holding upcoming_week back."""
    sched = nfl.load_schedules(seasons=[season])
    played = sched.filter(pl.col("home_score").is_not_null())
    unplayed = sched.filter(pl.col("home_score").is_null())
    upcoming = unplayed["week"].min() if unplayed.height else None
    last_played = played["week"].max() if played.height else None
    if upcoming is None:
        completed = last_played
    else:
        completed = upcoming - 1 if upcoming > 1 else None

    already_final = []
    unfinished = []
    if upcoming is not None:
        already_final = played.filter(pl.col("week") == upcoming)["game_id"].to_list()
        if last_played is not None:
            unfinished = unplayed.filter(pl.col("week") < last_played)["game_id"].to_list()
    return {
        "completed_week": completed,
        "upcoming_week": upcoming,
        "already_final_in_upcoming": already_final,
        "unfinished_games": unfinished,
    }


def main() -> None:
    args = parse_args()
    season = args.season or nfl.get_current_season()
    summary: dict = {"season": season, **detect_weeks(season)}
    week = args.week or summary["completed_week"]
    summary["stats_week"] = week

    if week is None:
        raise SystemExit(f"No completed games found for {season}.")

    if not args.dry_run:
        stats = nfl.load_player_stats(seasons=[season], summary_level="week")
        week_df = stats.filter(pl.col("week") == week)
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        out = OUT_DIR / f"player_stats_{season}_week{week}.csv"
        existed = out.exists()
        week_df.write_csv(out)
        summary.update(
            csv=str(out.relative_to(REPO_ROOT)).replace("\\", "/"),
            rows=week_df.height,
            overwrote_existing=existed,
        )
        print(f"Wrote {week_df.height} rows to {out}{' (overwrote existing)' if existed else ''}")
        if week_df.height < MIN_EXPECTED_ROWS:
            print(f"WARNING: only {week_df.height} rows; nflverse may not have published week {week} yet.")
        summary["low_row_count"] = week_df.height < MIN_EXPECTED_ROWS

    if summary["unfinished_games"]:
        print(f"WARNING: earlier games still without a final score (postponed?): {summary['unfinished_games']}")
    if summary["already_final_in_upcoming"]:
        print(
            f"WARNING: week {summary['upcoming_week']} has already started "
            f"({len(summary['already_final_in_upcoming'])} game(s) final) -- running mid-week."
        )

    print(json.dumps(summary))


if __name__ == "__main__":
    main()
