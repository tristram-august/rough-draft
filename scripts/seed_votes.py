# scripts/seed_votes.py
from __future__ import annotations

import argparse
import asyncio
import math
import random
import uuid
from dataclasses import dataclass
from typing import Iterable

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_sessionmaker
from app.models import DraftPick, PickVote


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Seed random community votes into pick_vote (DEV ONLY).")
    p.add_argument(
        "--years",
        required=True,
        help="Comma-separated years (e.g. 2020,2021,2022) or a range (e.g. 2000-2025).",
    )
    p.add_argument("--voters", type=int, default=5000, help="Number of unique fake anon voters.")
    p.add_argument("--seed", type=int, default=42, help="RNG seed for deterministic seeding.")
    p.add_argument("--chunk-size", type=int, default=5000, help="Insert chunk size.")
    p.add_argument("--prefix", default="seed-", help="Prefix for seeded voter_key so we can wipe safely.")
    p.add_argument("--wipe", action="store_true", help="Delete seeded votes first (matches voter_key prefix).")

    p.add_argument(
        "--mode",
        choices=("uniform", "realistic"),
        default="uniform",
        help="uniform: Poisson(avg) and fixed bias-success. realistic: rank-weighted volume + varied sentiment.",
    )

    # uniform mode knobs
    p.add_argument("--avg", type=float, default=40.0, help="[uniform] Average votes per pick (Poisson).")
    p.add_argument("--bias-success", type=float, default=0.5, help="[uniform] P(success) for every vote (0..1).")

    # realistic mode knobs
    p.add_argument("--avg-top", type=float, default=120.0, help="[realistic] Avg votes at pick #1.")
    p.add_argument("--min-avg", type=float, default=8.0, help="[realistic] Floor avg votes per pick.")
    p.add_argument(
        "--volume-alpha",
        type=float,
        default=0.85,
        help="[realistic] How fast volume decays by pick rank (higher=steeper).",
    )
    p.add_argument(
        "--early-success",
        type=float,
        default=0.62,
        help="[realistic] Baseline P(success) for early picks (higher rank quality).",
    )
    p.add_argument(
        "--late-success",
        type=float,
        default=0.48,
        help="[realistic] Baseline P(success) for late picks.",
    )
    p.add_argument(
        "--controversial-rate",
        type=float,
        default=0.10,
        help="[realistic] Fraction of picks that become controversial (votes ~50/50).",
    )
    p.add_argument(
        "--hot-take-rate",
        type=float,
        default=0.06,
        help="[realistic] Fraction of picks that skew strongly bust-ish.",
    )
    p.add_argument(
        "--conflict-jitter",
        type=float,
        default=0.06,
        help="[realistic] Random per-pick jitter applied to success probability.",
    )

    return p.parse_args()


def parse_years(spec: str) -> list[int]:
    s = spec.strip()
    if "-" in s:
        a, b = s.split("-", 1)
        start = int(a.strip())
        end = int(b.strip())
        if start > end:
            start, end = end, start
        return list(range(start, end + 1))
    years = []
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        years.append(int(part))
    if not years:
        raise ValueError("No years parsed from --years")
    return years


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def poisson(lam: float, rng: random.Random) -> int:
    """
    Knuth Poisson sampler.
    """
    if lam <= 0:
        return 0
    L = math.exp(-lam)
    k = 0
    p = 1.0
    while p > L:
        k += 1
        p *= rng.random()
    return k - 1


@dataclass(frozen=True)
class PickRef:
    pick_id: int
    year: int
    overall: int
    round: int


async def wipe_seeded(session: AsyncSession, prefix: str) -> int:
    stmt = (
        delete(PickVote)
        .where(PickVote.voter_type == "anon")
        .where(PickVote.voter_key.like(f"{prefix}%"))
    )
    res = await session.execute(stmt)
    return int(res.rowcount or 0)


def make_voter_pool(prefix: str, n: int) -> list[str]:
    return [f"{prefix}{uuid.uuid4()}" for _ in range(n)]


async def load_picks(session: AsyncSession, years: Iterable[int]) -> list[PickRef]:
    stmt = (
        select(DraftPick.id, DraftPick.year, DraftPick.overall, DraftPick.round)
        .where(DraftPick.year.in_(list(years)))
    )
    rows = (await session.execute(stmt)).all()
    picks = [PickRef(pick_id=r[0], year=r[1], overall=r[2], round=r[3]) for r in rows]
    picks.sort(key=lambda x: (x.year, x.overall))
    return picks


def success_prob_realistic(
    overall: int,
    max_overall: int,
    rng: random.Random,
    *,
    early_success: float,
    late_success: float,
    controversial_rate: float,
    hot_take_rate: float,
    conflict_jitter: float,
) -> float:
    """
    Creates a per-pick probability of success that is:
      - generally higher early, lower late
      - sometimes controversial (~50/50)
      - sometimes hot-take bust-lean
      - includes small noise so it doesn't look synthetic
    """
    # baseline drift by pick rank
    t = (overall - 1) / max(1, max_overall - 1)
    base = (1 - t) * early_success + t * late_success

    r = rng.random()
    if r < controversial_rate:
        base = 0.5 + rng.uniform(-0.03, 0.03)
    elif r < controversial_rate + hot_take_rate:
        base = rng.uniform(0.18, 0.38)  # busty

    base += rng.uniform(-conflict_jitter, conflict_jitter)
    return clamp(base, 0.05, 0.95)


def avg_votes_realistic(
    overall: int,
    *,
    avg_top: float,
    min_avg: float,
    alpha: float,
    rng: random.Random,
) -> float:
    """
    Volume decays with overall pick number.
    avg(overall) = min_avg + (avg_top - min_avg) / (overall ** alpha)
    plus small multiplicative noise per pick.
    """
    lam = min_avg + (avg_top - min_avg) / (overall ** alpha)
    lam *= rng.uniform(0.85, 1.15)
    return max(0.0, lam)


def generate_votes_for_pick_uniform(
    pick: PickRef,
    voter_pool: list[str],
    *,
    avg: float,
    bias_success: float,
    rng: random.Random,
) -> list[dict]:
    k = poisson(avg, rng)
    if k <= 0:
        return []
    k = min(k, len(voter_pool))
    voters = rng.sample(voter_pool, k)
    return [
        {
            "pick_id": pick.pick_id,
            "voter_type": "anon",
            "voter_key": voter_key,
            "value": "success" if rng.random() < bias_success else "bust",
        }
        for voter_key in voters
    ]


def generate_votes_for_pick_realistic(
    pick: PickRef,
    voter_pool: list[str],
    *,
    max_overall: int,
    avg_top: float,
    min_avg: float,
    volume_alpha: float,
    early_success: float,
    late_success: float,
    controversial_rate: float,
    hot_take_rate: float,
    conflict_jitter: float,
    rng: random.Random,
) -> list[dict]:
    lam = avg_votes_realistic(pick.overall, avg_top=avg_top, min_avg=min_avg, alpha=volume_alpha, rng=rng)
    k = poisson(lam, rng)
    if k <= 0:
        return []
    k = min(k, len(voter_pool))
    voters = rng.sample(voter_pool, k)

    p_success = success_prob_realistic(
        pick.overall,
        max_overall,
        rng,
        early_success=early_success,
        late_success=late_success,
        controversial_rate=controversial_rate,
        hot_take_rate=hot_take_rate,
        conflict_jitter=conflict_jitter,
    )
    return [
        {
            "pick_id": pick.pick_id,
            "voter_type": "anon",
            "voter_key": voter_key,
            "value": "success" if rng.random() < p_success else "bust",
        }
        for voter_key in voters
    ]


async def flush_votes(session: AsyncSession, rows: list[dict]) -> None:
    if not rows:
        return
    stmt = insert(PickVote).values(rows)
    stmt = stmt.on_conflict_do_nothing(constraint="uq_vote_one_per_voter_per_pick")
    await session.execute(stmt)


async def main() -> None:
    args = parse_args()

    years = parse_years(args.years)
    rng = random.Random(args.seed)

    if args.mode == "uniform":
        if not (0.0 <= args.bias_success <= 1.0):
            raise SystemExit("--bias-success must be between 0.0 and 1.0")
        if args.avg < 0:
            raise SystemExit("--avg must be >= 0")

    if args.mode == "realistic":
        for name in ("early_success", "late_success", "controversial_rate", "hot_take_rate", "conflict_jitter"):
            v = float(getattr(args, name))
            if v < 0 or (name.endswith("success") and v > 1.0) or (not name.endswith("success") and v > 1.0):
                raise SystemExit(f"--{name} must be within [0,1]")
        if args.avg_top < 0 or args.min_avg < 0:
            raise SystemExit("--avg-top and --min-avg must be >= 0")

    session_maker = get_sessionmaker()
    async with session_maker() as session:  # type: AsyncSession
        if args.wipe:
            deleted = await wipe_seeded(session, args.prefix)
            await session.commit()
            print(f"Wiped {deleted} seeded votes (prefix='{args.prefix}').")

        voter_pool = make_voter_pool(args.prefix, args.voters)
        picks = await load_picks(session, years)
        if not picks:
            raise SystemExit(f"No draft picks found for years: {years}")

        max_overall = max(p.overall for p in picks)

        pending: list[dict] = []
        total_votes = 0

        # Small per-year variation so years don't look identical
        year_noise = {y: rng.uniform(0.92, 1.08) for y in set(p.year for p in picks)}

        for p in picks:
            if args.mode == "uniform":
                rows = generate_votes_for_pick_uniform(
                    pick=p,
                    voter_pool=voter_pool,
                    avg=args.avg,
                    bias_success=args.bias_success,
                    rng=rng,
                )
            else:
                # per-year tweak to top volume and base success
                yn = year_noise[p.year]
                rows = generate_votes_for_pick_realistic(
                    pick=p,
                    voter_pool=voter_pool,
                    max_overall=max_overall,
                    avg_top=args.avg_top * yn,
                    min_avg=args.min_avg,
                    volume_alpha=args.volume_alpha,
                    early_success=clamp(args.early_success + (yn - 1) * 0.05, 0.05, 0.95),
                    late_success=clamp(args.late_success + (yn - 1) * 0.02, 0.05, 0.95),
                    controversial_rate=args.controversial_rate,
                    hot_take_rate=args.hot_take_rate,
                    conflict_jitter=args.conflict_jitter,
                    rng=rng,
                )

            if rows:
                pending.extend(rows)
                total_votes += len(rows)

            if len(pending) >= args.chunk_size:
                await flush_votes(session, pending)
                await session.commit()
                pending.clear()

        if pending:
            await flush_votes(session, pending)
            await session.commit()

        print(
            "Done. "
            f"mode={args.mode} years={years} voters={args.voters} total_votes≈{total_votes} "
            f"prefix='{args.prefix}' seed={args.seed}"
        )


if __name__ == "__main__":
    asyncio.run(main())