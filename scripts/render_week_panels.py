"""
Render one week's Outperformed / Underperformed blog panels from the
Projection Misses page (output/social/projection_misses.html).

    python scripts/render_week_panels.py 8

Add the week to that page's DATA first. Writes
output/social/week_<N>_panels/week_<N>_over.png and _under.png, in the same
dark style and ~511px width as the earlier weekly blog images.
"""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

SOURCE = Path("output/social/projection_misses.html")


def main() -> None:
    week = int(sys.argv[1])
    out = Path(f"output/social/week_{week}_panels")
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 1200}, color_scheme="dark")
        page.goto(SOURCE.resolve().as_uri(), wait_until="networkidle")
        panels = page.locator(f"#week{week} .panel")
        if panels.count() < 2:
            raise SystemExit(f"Week {week} isn't on {SOURCE} yet -- add it to DATA first.")
        for kind, idx in (("over", 0), ("under", 1)):
            path = out / f"week_{week}_{kind}.png"
            panels.nth(idx).screenshot(path=str(path))
            print(f"wrote {path}")
        browser.close()


if __name__ == "__main__":
    main()
