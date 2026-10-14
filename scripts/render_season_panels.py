"""
Screenshot the season-to-date Beat/Bust/Met panels for blog use -- the same
narrow list-card style as the "Projection Misses" write-up, not the square
Instagram carousel (see render_social_slides.py for that).

    python scripts/render_season_panels.py
    python scripts/render_season_panels.py --min-projected 25 --limit 5

Requires the frontend dev server (or a deployed instance) reachable at
--base-url, and the `social` extra installed (see render_social_slides.py).
Each image is clipped to the panel's own size -- width is fixed, height
follows however many rows are shown.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

VIEWPORT = {"width": 900, "height": 1000}
DEVICE_SCALE_FACTOR = 2
READY_SELECTOR = '[data-slide-ready="true"]'
READY_TIMEOUT_MS = 15_000
DEFAULT_LIMIT = 6

KINDS = {
    "over": "beat",
    "under": "bust",
    "met": "met",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--season", type=int, default=None, help="Defaults to the latest season the app has.")
    p.add_argument("--scoring", default="ppr", choices=["ppr", "half", "std"])
    p.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    p.add_argument(
        "--min-projected",
        type=float,
        default=30.0,
        help="Only players projected at least this many points are eligible for the Met panel.",
    )
    p.add_argument("--base-url", default="http://localhost:3000")
    p.add_argument("--out-dir", default="output/social/season_panels")
    return p.parse_args()


def panel_url(base_url: str, kind: str, *, season: int | None, scoring: str, limit: int, min_projected: float) -> str:
    params = [f"kind={kind}", f"scoring={scoring}", f"limit={limit}", f"minProjected={min_projected}"]
    if season is not None:
        params.append(f"season={season}")
    return f"{base_url}/social/season-panel?{'&'.join(params)}"


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT, device_scale_factor=DEVICE_SCALE_FACTOR)
        for kind, name in KINDS.items():
            url = panel_url(args.base_url, kind, season=args.season, scoring=args.scoring, limit=args.limit, min_projected=args.min_projected)
            page.goto(url, wait_until="networkidle")
            panel = page.locator(READY_SELECTOR)
            panel.wait_for(state="visible", timeout=READY_TIMEOUT_MS)
            out_path = out_dir / f"season_{name}.png"
            panel.screenshot(path=str(out_path))
            print(f"  season_{name}.png  <-  {url}")
        browser.close()

    print(f"Done -- {len(KINDS)} panels written to {out_dir}/")


if __name__ == "__main__":
    main()
