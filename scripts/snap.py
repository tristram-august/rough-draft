"""
Screenshot one element (or a whole page) of the site into a blog image.

    # single shot -- path is relative to the site, out is relative to public/blog/
    python scripts/snap.py --url /fantasy/player/00-0039337 \\
        --selector "div.rounded-3xl:below(h2:has-text('Game log'))" --out wr-2024/nabers-games.png

    # click things first (repeatable, run in order), wait for something, pad the crop
    python scripts/snap.py --url /draft --click "text=2024" --click "text=Malik Nabers" \\
        --wait-for "[role=dialog]" --selector "[role=dialog]" --pad 0 --out wr-2024/nabers-stats.png

    # batch: one browser for many shots (JSON list; top-level "defaults" optional)
    python scripts/snap.py --spec shots.json

Defaults: https://roughdraftfootball.com (production data, nothing to start
locally); --local switches to http://localhost:3000 for UI that isn't
deployed yet. Dark mode, 1280px-wide viewport, 2x device scale, 12px of page
background around the element. Selectors are Playwright selectors, so CSS,
text=..., :has-text(), :below(), >> chaining, etc. all work.

Spec file shape:
    {"defaults": {"pad": 12, "width": 1280},
     "shots": [{"url": "/teams/MIN", "selector": "...", "out": "post/min.png",
                "click": ["text=Schedule"], "wait_for": "...", "nth": 0}]}

Each saved file under frontend/.../public/ is printed with its site path
(e.g. /blog/wr-2024/nabers-games.png) -- that's what goes in the post.
Exits non-zero if any shot fails, after trying the rest.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urljoin

from playwright.sync_api import Page, sync_playwright

REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DIR = REPO_ROOT / "frontend" / "rough-draft-ui" / "public"
BLOG_DIR = PUBLIC_DIR / "blog"
PROD_URL = "https://roughdraftfootball.com"
LOCAL_URL = "http://localhost:3000"
HIDE_CSS = "nextjs-portal { display: none !important; }"  # dev-mode error overlay badge
DEFAULTS = {"width": 1280, "height": 900, "scale": 2, "pad": 12, "nth": None,
            "click": [], "wait_for": None, "settle_ms": 400, "full_page": False}


def resolve_out(out: str) -> Path:
    p = Path(out)
    if p.is_absolute():
        return p
    if p.parts and p.parts[0] in ("frontend", "output", "data"):  # repo-relative
        return REPO_ROOT / p
    return BLOG_DIR / p


def site_path(path: Path) -> str | None:
    try:
        return "/" + path.resolve().relative_to(PUBLIC_DIR.resolve()).as_posix()
    except ValueError:
        return None


def capture(page: Page, base: str, shot: dict) -> Path:
    url = shot["url"] if shot["url"].startswith("http") else urljoin(base + "/", shot["url"].lstrip("/"))
    page.set_viewport_size({"width": shot["width"], "height": shot["height"]})
    page.goto(url, wait_until="networkidle", timeout=60_000)
    page.add_style_tag(content=HIDE_CSS)

    for sel in shot["click"]:
        page.locator(sel).first.click(timeout=15_000)
        page.wait_for_load_state("networkidle")
    if shot["wait_for"]:
        page.locator(shot["wait_for"]).first.wait_for(state="visible", timeout=20_000)
    page.wait_for_timeout(shot["settle_ms"])  # let transitions/fonts finish

    out = resolve_out(shot["out"])
    out.parent.mkdir(parents=True, exist_ok=True)

    if not shot.get("selector"):
        page.screenshot(path=str(out), full_page=shot["full_page"])
        return out

    loc = page.locator(shot["selector"])
    count = loc.count()
    if count == 0:
        raise RuntimeError(f"selector matched nothing: {shot['selector']}")
    if count > 1 and shot["nth"] is None:
        print(f"  note: selector matched {count} elements, using the first (set nth to pick)")
    el = loc.nth(shot["nth"] or 0)
    el.scroll_into_view_if_needed()
    # Sticky/fixed chrome (the site header) gets painted over tall captures --
    # hide any that isn't the target, inside it, or wrapping it.
    page.evaluate(
        """target => { for (const n of document.querySelectorAll('body *')) {
               const pos = getComputedStyle(n).position;
               if ((pos === 'fixed' || pos === 'sticky') && !n.contains(target) && !target.contains(n))
                   n.style.setProperty('visibility', 'hidden', 'important');
           } }""",
        el.element_handle(),
    )

    pad = shot["pad"]
    if pad <= 0:
        el.screenshot(path=str(out))
        return out
    box = page.evaluate(
        """el => { const r = el.getBoundingClientRect();
                   return {x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height,
                           pw: document.documentElement.scrollWidth, ph: document.documentElement.scrollHeight}; }""",
        el.element_handle(),
    )
    x, y = max(box["x"] - pad, 0), max(box["y"] - pad, 0)
    clip = {"x": x, "y": y,
            "width": min(box["x"] + box["w"] + pad, box["pw"]) - x,
            "height": min(box["y"] + box["h"] + pad, box["ph"]) - y}
    page.screenshot(path=str(out), clip=clip, full_page=True)
    return out


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--spec", type=Path, help="JSON batch file (see above).")
    p.add_argument("--url", help="Site path (/teams/MIN) or full URL.")
    p.add_argument("--selector", help="Element to capture; omit for the whole viewport.")
    p.add_argument("--out", help="Output PNG, relative to public/blog/ unless absolute/repo-relative.")
    p.add_argument("--click", action="append", default=[], help="Selector to click first (repeatable, in order).")
    p.add_argument("--wait-for", dest="wait_for", help="Selector that must be visible before capture.")
    p.add_argument("--nth", type=int, help="Which match to use when the selector matches several (0-based).")
    p.add_argument("--pad", type=int, help=f"Page background around the element in CSS px (default {DEFAULTS['pad']}; 0 = tight).")
    p.add_argument("--width", type=int, help=f"Viewport width (default {DEFAULTS['width']}).")
    p.add_argument("--height", type=int, help=f"Viewport height (default {DEFAULTS['height']}).")
    p.add_argument("--scale", type=float, help=f"Device scale factor (default {DEFAULTS['scale']}).")
    p.add_argument("--full-page", dest="full_page", action="store_true", help="Whole scrolling page (no selector).")
    p.add_argument("--base-url", help=f"Site root (default {PROD_URL}).")
    p.add_argument("--local", action="store_true", help=f"Use {LOCAL_URL} instead of production.")
    args = p.parse_args()

    if args.spec:
        spec = json.loads(args.spec.read_text(encoding="utf-8"))
        defaults = {**DEFAULTS, **spec.get("defaults", {})}
        shots = [{**defaults, **s} for s in spec["shots"]]
    else:
        if not (args.url and args.out):
            p.error("--url and --out are required without --spec")
        cli = {k: v for k, v in vars(args).items()
               if k in ("url", "selector", "out", "click", "wait_for", "nth", "pad", "width", "height", "scale", "full_page")
               and v not in (None, [], False)}
        shots = [{**DEFAULTS, **cli}]

    base = (args.base_url or (LOCAL_URL if args.local else PROD_URL)).rstrip("/")
    failures = 0
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        # one context per scale factor (it's fixed per context)
        contexts: dict[float, object] = {}
        for shot in shots:
            scale = shot["scale"]
            if scale not in contexts:
                contexts[scale] = browser.new_context(device_scale_factor=scale, color_scheme="dark")
            page = contexts[scale].new_page()
            try:
                out = capture(page, base, shot)
                print(f"OK   {out.relative_to(REPO_ROOT).as_posix() if out.is_relative_to(REPO_ROOT) else out}"
                      + (f"  ->  {site_path(out)}" if site_path(out) else ""))
            except Exception as e:  # keep going; report at the end
                failures += 1
                print(f"FAIL {shot.get('out')}: {str(e).splitlines()[0]}")
            finally:
                page.close()
        browser.close()
    if failures:
        print(f"{failures} of {len(shots)} shot(s) failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
