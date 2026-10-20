"""
Render playoff-odds Instagram slides and blog panels from /social/playoffs.

    python scripts/render_playoff_slides.py --conf AFC
    python scripts/render_playoff_slides.py --conf both --week 6

Needs the frontend (and the API behind it) running. Writes to
output/social/playoffs_week_<N>/<conf>/ (slides) and .../blog/ (panels).
"""
from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

SLIDE_VIEWPORT = {"width": 1080, "height": 1350}
PANEL_VIEWPORT = {"width": 900, "height": 1200}
DEVICE_SCALE_FACTOR = 2
READY_SELECTOR = '[data-slide-ready="true"]'
READY_TIMEOUT_MS = 15_000
HIDE_DEV_OVERLAY = "nextjs-portal { display: none !important; }"
DIVISIONS = ["East", "North", "South", "West"]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--conf", default="both", choices=["AFC", "NFC", "both"])
    p.add_argument("--week", type=int, default=None, help="Odds as of this week (defaults to the latest).")
    p.add_argument("--base-url", default="http://localhost:3000")
    p.add_argument("--api-url", default="http://localhost:8000/api")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    query = f"?week={args.week}" if args.week is not None else ""
    week = json.load(urllib.request.urlopen(f"{args.api_url}/playoffs/odds{query}"))["week"]
    root = Path(f"output/social/playoffs_week_{week}")
    confs = ["AFC", "NFC"] if args.conf == "both" else [args.conf]

    def url(conf: str, slide: str, division: str | None = None) -> str:
        q = f"conf={conf}&slide={slide}&week={week}"
        return f"{args.base_url}/social/playoffs?{q}" + (f"&division={division}" if division else "")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        slide_page = browser.new_page(viewport=SLIDE_VIEWPORT, device_scale_factor=DEVICE_SCALE_FACTOR)
        panel_page = browser.new_page(viewport=PANEL_VIEWPORT, device_scale_factor=DEVICE_SCALE_FACTOR)

        def shoot(page, target: str, out: Path, element: bool) -> None:
            page.goto(target, wait_until="networkidle")
            page.wait_for_selector(READY_SELECTOR, timeout=READY_TIMEOUT_MS)
            page.add_style_tag(content=HIDE_DEV_OVERLAY)
            out.parent.mkdir(parents=True, exist_ok=True)
            (page.locator(READY_SELECTOR).screenshot if element else page.screenshot)(path=str(out))
            print(f"  {out}")

        for conf in confs:
            plan = [("01_cover", "cover", None), ("02_odds", "table", None)]
            plan += [(f"0{3 + i}_{d.lower()}", "division", d) for i, d in enumerate(DIVISIONS)]
            plan.append(("07_cta", "cta", None))
            for name, slide, division in plan:
                shoot(slide_page, url(conf, slide, division), root / conf.lower() / f"{name}.png", element=False)

            blog = root / "blog"
            shoot(panel_page, url(conf, "panel-table"), blog / f"{conf.lower()}_odds.png", element=True)
            for d in DIVISIONS:
                shoot(panel_page, url(conf, "panel-division", d), blog / f"{conf.lower()}_{d.lower()}.png", element=True)
        browser.close()
    print(f"Done -- odds as of week {week}, written under {root}/")


if __name__ == "__main__":
    main()
