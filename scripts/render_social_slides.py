"""
Screenshot the /social/boom-bust slides into PNGs ready to upload to
Instagram as a carousel -- for one week, or for the season so far.

    python scripts/render_social_slides.py --week 3
    python scripts/render_social_slides.py --week 3 --spotlight 00-0032950
    python scripts/render_social_slides.py --season-to-date
    python scripts/render_social_slides.py --season-to-date --min-projected 25

Requires the frontend dev server (or a deployed instance) reachable at
--base-url, and the `social` extra installed:

    .venv/Scripts/python.exe -m pip install -e .[social]
    .venv/Scripts/python.exe -m playwright install chromium

Renders at 2x device scale so the images stay sharp after Instagram's own
compression, even though the page itself is laid out at 1080x1350 CSS
pixels -- see app/social/boom-bust/page.tsx.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

VIEWPORT = {"width": 1080, "height": 1350}
DEVICE_SCALE_FACTOR = 2
READY_SELECTOR = '[data-slide-ready="true"]'
READY_TIMEOUT_MS = 15_000
DEFAULT_LIMIT = 6


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    week_group = p.add_mutually_exclusive_group(required=True)
    week_group.add_argument("--week", type=int, help="Render one week's slides.")
    week_group.add_argument("--season-to-date", action="store_true", help="Render season-so-far slides instead.")
    p.add_argument("--season", type=int, default=None, help="Defaults to the latest season the app has.")
    p.add_argument("--scoring", default="ppr", choices=["ppr", "half", "std"])
    p.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="Rows per Over/Under/Met slide.")
    p.add_argument(
        "--min-projected",
        type=float,
        default=30.0,
        help="Only players projected at least this many points are eligible for the Met-projection slide.",
    )
    p.add_argument("--no-met", action="store_true", help="Skip the Closest-to-Projection slide.")
    p.add_argument("--spotlight", default=None, help="gsis_id to feature; defaults to the top overperformer.")
    p.add_argument("--base-url", default="http://localhost:3000")
    p.add_argument("--out-dir", default=None, help="Defaults to output/social/week_<N>/ or .../season/")
    return p.parse_args()


def slide_url(
    base_url: str,
    slide: str,
    *,
    week: int | None,
    season: int | None,
    scoring: str,
    limit: int,
    min_projected: float,
    spotlight: str | None = None,
) -> str:
    params = [f"slide={slide}", f"scoring={scoring}", f"limit={limit}", f"minProjected={min_projected}"]
    if week is not None:
        params.append(f"week={week}")
    if season is not None:
        params.append(f"season={season}")
    if spotlight:
        params.append(f"spotlight={spotlight}")
    return f"{base_url}/social/boom-bust?{'&'.join(params)}"


def build_plan(args: argparse.Namespace) -> list[tuple[str, str]]:
    """(filename, url) pairs, numbered so they sort into upload order."""
    week = None if args.season_to_date else args.week
    common = dict(week=week, season=args.season, scoring=args.scoring, limit=args.limit, min_projected=args.min_projected)
    plan = [
        ("01_cover.png", slide_url(args.base_url, "cover", **common)),
        ("02_over.png", slide_url(args.base_url, "over", **common)),
        ("03_under.png", slide_url(args.base_url, "under", **common)),
    ]
    n = 4
    if not args.no_met:
        plan.append((f"0{n}_met.png", slide_url(args.base_url, "met", **common)))
        n += 1
    plan.append((f"0{n}_spotlight.png", slide_url(args.base_url, "spotlight", spotlight=args.spotlight, **common)))
    n += 1
    plan.append((f"0{n}_cta.png", slide_url(args.base_url, "cta", **common)))
    return plan


def main() -> None:
    args = parse_args()
    default_dir = f"output/social/week_{args.week}" if args.week else "output/social/season"
    out_dir = Path(args.out_dir or default_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    plan = build_plan(args)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT, device_scale_factor=DEVICE_SCALE_FACTOR)
        for filename, url in plan:
            page.goto(url, wait_until="networkidle")
            page.wait_for_selector(READY_SELECTOR, timeout=READY_TIMEOUT_MS)
            out_path = out_dir / filename
            page.screenshot(path=str(out_path))
            print(f"  {filename}  <-  {url}")
        browser.close()

    print(f"Done -- {len(plan)} slides written to {out_dir}/")


if __name__ == "__main__":
    main()
