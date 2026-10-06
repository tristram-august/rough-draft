"""Rolling backtest of the receiving-prop probability engine vs. a naive baseline.

For every receiver-game in [first, last], predict P(stat >= t) using only data
before that game, then score against the actual result. Lower Brier is better.

Usage:
    python scripts/backtest_receiving_props.py --stat rec_yards --first 2017 --last 2024
    python scripts/backtest_receiving_props.py --stat receptions --first 2025 --last 2026
"""
from __future__ import annotations

import argparse
import dataclasses
from pathlib import Path

import app.betting.engine as engine
from app.betting.engine import STATS, backtest, load_receiver_games

FIRST_DATA_SEASON = 2016


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data-dir", type=Path, default=Path("data/player_stats"))
    p.add_argument("--stat", choices=sorted(STATS), default="rec_yards")
    p.add_argument("--first", type=int, default=2017)
    p.add_argument("--last", type=int, default=2026)
    p.add_argument("--bandwidth", type=float, default=None)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if args.bandwidth is not None:
        engine.STATS[args.stat] = dataclasses.replace(STATS[args.stat], min_bandwidth=args.bandwidth)
    games = load_receiver_games(args.data_dir, range(FIRST_DATA_SEASON, args.last + 1))
    result = backtest(games, args.first, args.last, stat=args.stat)

    print(f"Stat: {args.stat}  seasons {args.first}-{args.last}")
    print(f"Predictions scored: {result['predictions']} (player-game x threshold)")
    print(f"Brier model:    {result['brier_model']}")
    print(f"Brier baseline: {result['brier_baseline']}")
    print("Calibration (model): predicted vs actual hit rate")
    for b in result["buckets"]:
        print(f"  predicted={b['predicted']:.3f}  actual={b['actual']:.3f}  n={b['n']}")


if __name__ == "__main__":
    main()
