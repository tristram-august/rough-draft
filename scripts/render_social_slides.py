"""
Screenshot the /social/boom-bust slides for one week into PNGs ready to
upload to Instagram as a carousel.

    python scripts/render_social_slides.py --week 3
    python scripts/render_social_slides.py --week 3 --pages 2 --spotlight 00-0032950

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


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Render the weekly boom/bust Instagram carousel to PNGs.")
    p.add_argument("--week", type=int, required=True)
    p.add_argument("--season", type=int, default=None, help="Defaults to the latest season the app has.")
    p.add_argument("--scoring", default="ppr", choices=["ppr", "half", "std"])
    p.add_argument("--pages", type=int, default=1, choices=[1, 2], help="1 = top 6 per list, 2 = top 12.")
    p.add_argument("--spotlight", default=None, help="gsis_id to feature; defaults to the top overperformer.")
    p.add_argument("--base-url", default="http://localhost:3000")
    p.add_argument("--out-dir", default=None, help="Defaults to output/social/week_<N>/")
    return p.parse_args()


def slide_url(base_url: str, week: int, slide: str, *, season: int | None, scoring: str, page: int = 1, spotlight: str | None = None) -> str:
    params = [f"week={week}", f"slide={slide}", f"scoring={scoring}"]
    if season is not None:
        params.append(f"season={season}")
    if page > 1:
        params.append(f"page={page}")
    if spotlight:
        params.append(f"spotlight={spotlight}")
    return f"{base_url}/social/boom-bust?{'&'.join(params)}"


def build_plan(args: argparse.Namespace) -> list[tuple[str, str]]:
    """(filename, url) pairs, numbered so they sort into upload order."""
    common = dict(season=args.season, scoring=args.scoring)
    plan = [
        ("01_cover.png", slide_url(args.base_url, args.week, "cover", **common)),
        ("02_over.png", slide_url(args.base_url, args.week, "over", **common)),
    ]
    n = 3
    if args.pages == 2:
        plan.append((f"0{n}_over_2.png", slide_url(args.base_url, args.week, "over", page=2, **common)))
        n += 1
    plan.append((f"0{n}_under.png", slide_url(args.base_url, args.week, "under", **common)))
    n += 1
    if args.pages == 2:
        plan.append((f"0{n}_under_2.png", slide_url(args.base_url, args.week, "under", page=2, **common)))
        n += 1
    plan.append((f"0{n}_spotlight.png", slide_url(args.base_url, args.week, "spotlight", spotlight=args.spotlight, **common)))
    n += 1
    plan.append((f"0{n}_cta.png", slide_url(args.base_url, args.week, "cta", **common)))
    return plan


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir or f"output/social/week_{args.week}")
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
