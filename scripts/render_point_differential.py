"""
Diverging team-margin blog panels: one bar per team, sorted best to worst.

    python scripts/render_point_differential.py                              # point differential
    python scripts/render_point_differential.py --metric turnover-margin     # takeaways - giveaways
    python scripts/render_point_differential.py --out team-stats/point-differential-week-9.png

Reads the production API by default (same data the site shows), so nothing
needs to run locally. Writes a 2x PNG to public/blog/<out> (default
team-stats/<metric>.png) and prints the /blog/... path to paste.

Same dark panel style and blue/red diverging pair as
render_season_weekly_panels.py (validated with the dataviz palette checker on
the #141a22 surface). Bars carry the polarity color; numbers stay in text ink.
"""
from __future__ import annotations

import argparse
import json
import tempfile
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parents[1]
BLOG_DIR = REPO_ROOT / "frontend" / "rough-draft-ui" / "public" / "blog"
PROD_API = "https://rough-draft-production.up.railway.app/api"

TEMPLATE = """<!doctype html><html><head><meta charset="utf-8"><style>
:root{--bg:#0d1117;--surface:#141a22;--surface-2:#1a212b;--border:#262e39;--text:#e6e8eb;--muted:#8b94a3;--faint:#5f6b7d;
--pos:#3987e5;--neg:#e66767;--zero:#525b68;--grid:#1f2731}
*{box-sizing:border-box}body{margin:0;background:var(--bg);padding:12px}
.panel{width:680px;background:var(--surface);border:1px solid var(--border);border-radius:14px;overflow:hidden;
font-family:"IBM Plex Sans",-apple-system,"Segoe UI",sans-serif;color:var(--text)}
.head{display:flex;align-items:center;gap:8px;padding:13px 16px;border-bottom:1px solid var(--border);background:var(--surface-2)}
.head .dot{width:8px;height:8px;border-radius:50%;background:var(--pos)}.head h3{font-size:13px;margin:0;font-weight:650}
.head .period{margin-left:auto;font-size:10.5px;color:var(--faint);font-family:"IBM Plex Mono",monospace}
.sub{padding:12px 16px 0;margin:0;font-size:11px;color:var(--muted);line-height:1.5}
.legend{display:flex;gap:14px;align-items:center;padding:10px 16px 2px;font-size:10px;color:var(--muted)}
.legend .sw{display:inline-block;width:8px;height:8px;border-radius:2px;margin-right:5px;vertical-align:-1px}
.grid{display:grid;grid-template-columns:20px 200px 1fr 46px 70px;align-items:center;column-gap:8px}
.heads{padding:12px 16px 4px;font-family:"IBM Plex Mono",monospace;font-size:9px;letter-spacing:.05em;text-transform:uppercase;color:var(--faint)}
.r{text-align:right}
.rows{padding:0 16px 10px}.row{height:22px;margin-top:2px}
.rk{font-family:"IBM Plex Mono",monospace;font-size:10px;color:var(--faint)}
.who{display:flex;align-items:center;gap:6px;min-width:0}
.ab{flex:none;width:30px;font-size:9.5px;font-weight:700;color:var(--muted);font-family:"IBM Plex Mono",monospace}
.name{font-size:12px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.track{position:relative;height:100%}
.track::before{content:"";position:absolute;left:50%;top:-2px;bottom:-2px;width:1px;background:var(--zero)}
.bar{position:absolute;top:5px;height:12px}
.bar.pos{left:50%;background:var(--pos);border-radius:0 4px 4px 0}
.bar.neg{right:50%;background:var(--neg);border-radius:4px 0 0 4px}
.val{font-family:"IBM Plex Mono",monospace;font-size:12px;font-weight:700;text-align:right}
.pg{font-family:"IBM Plex Mono",monospace;font-size:10px;color:var(--muted);text-align:right;white-space:nowrap}
.axis{padding:2px 16px 0}.axis .track::before{display:none}
.tick{position:absolute;transform:translateX(-50%);font-family:"IBM Plex Mono",monospace;font-size:8.5px;color:var(--faint)}
footer{padding:10px 16px 14px;font-size:9.5px;color:var(--faint);line-height:1.5;border-top:1px solid var(--border)}
</style></head><body><div class="panel" id="chart"></div><script>
const CFG = __CFG__;
const sgn = n => n > 0 ? "+" + n : n < 0 ? "\\u2212" + Math.abs(n) : "0";
const sgn1 = n => (n > 0 ? "+" : n < 0 ? "\\u2212" : "") + Math.abs(n).toFixed(1);
const MAX = Math.max(1, ...CFG.rows.map(r => Math.abs(r.diff)));
// Round the scale up to a tidy tick step so the axis labels are clean numbers.
const STEP = MAX > 150 ? 50 : MAX > 60 ? 25 : MAX > 25 ? 10 : MAX > 10 ? 5 : 2, LIM = Math.ceil(MAX / STEP) * STEP;
const pct = v => (Math.abs(v) / LIM * 50).toFixed(2) + "%";
const ticks = [];
for (let t = -LIM; t <= LIM; t += STEP) ticks.push(`<span class="tick" style="left:${50 + t / LIM * 50}%">${sgn(t)}</span>`);
document.getElementById("chart").innerHTML = `
  <div class="head"><span class="dot"></span><h3>${CFG.title}</h3><span class="period">${CFG.period}</span></div>
  <p class="sub">${CFG.sub}</p>
  <div class="legend"><span><span class="sw" style="background:var(--pos)"></span>${CFG.pos_label}</span>
    <span><span class="sw" style="background:var(--neg)"></span>${CFG.neg_label}</span></div>
  <div class="grid heads"><span>#</span><span>Team</span><span></span><span class="r">${CFG.value_label}</span><span class="r">${CFG.extra_label}</span></div>
  <div class="rows">${CFG.rows.map((r, i) => {
    const s = r.diff > 0 ? "pos" : r.diff < 0 ? "neg" : "";
    const bar = s ? `<div class="bar ${s}" style="width:${pct(r.diff)}"></div>` : "";
    return `<div class="grid row">
      <span class="rk">${i + 1}</span>
      <div class="who"><span class="ab">${r.team}</span><span class="name">${r.name}</span></div>
      <div class="track">${bar}</div>
      <span class="val">${sgn(r.diff)}</span>
      <span class="pg">${r.extra ?? sgn1(r.diff / r.games)}</span></div>`;
  }).join("")}</div>
  <div class="grid axis"><span></span><span></span><div class="track" style="height:12px">${ticks.join("")}</div><span></span><span></span></div>
  <footer>${CFG.foot}</footer>`;
</script></body></html>"""


METRICS = {
    "point-differential": {
        "title": "Point differential",
        "sub": "Points scored minus points allowed this regular season. Bars share one scale; "
               "per-game evens out teams that have already had their bye.",
        "pos_label": "Outscoring opponents", "neg_label": "Being outscored",
        "value_label": "Diff", "extra_label": "Per game",
        "row": lambda r: {"diff": r["points_for"] - r["points_against"]},
    },
    "turnover-margin": {
        "title": "Turnover margin",
        "sub": "Takeaways minus giveaways this regular season. Ties are ordered by per-game "
               "margin, then by takeaways.",
        "pos_label": "More takeaways than giveaways", "neg_label": "More giveaways than takeaways",
        "value_label": "Margin", "extra_label": "TK – GV",
        "row": lambda r: {"diff": r["turnover_margin"], "tiebreak": r["takeaways"],
                          "extra": f"{r['takeaways']} – {r['giveaways']}"},
    },
}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--metric", default="point-differential", choices=sorted(METRICS))
    p.add_argument("--season", type=int, default=2026)
    p.add_argument("--api-url", default=PROD_API)
    p.add_argument("--out", default=None, help="Relative to public/blog/ (default team-stats/<metric>.png).")
    args = p.parse_args()
    metric = METRICS[args.metric]
    args.out = args.out or f"team-stats/{args.metric}.png"

    url = f"{args.api_url}/teams/stats?season={args.season}&sort=points_for&direction=desc"
    data = json.load(urllib.request.urlopen(url, timeout=30))
    rows = [{"team": r["team"], "name": r["team_name"], "games": r["games"], **metric["row"](r)}
            for r in data["rows"] if r["games"]]
    # Ties (common for turnovers) break on the per-game rate, then the secondary key.
    rows.sort(key=lambda r: (-r["diff"], -r["diff"] / r["games"], -r.get("tiebreak", 0), r["name"]))
    max_games = max(r["games"] for r in rows)

    cfg = {
        **{k: v for k, v in metric.items() if k != "row"},
        "period": f"{args.season} · through {max_games} games",
        "foot": "Source: nflverse team stats via roughdraftfootball.com/teams",
        "rows": rows,
    }
    html = TEMPLATE.replace("__CFG__", json.dumps(cfg))

    out = BLOG_DIR / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "panel.html"
        src.write_text(html, encoding="utf-8")
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 760, "height": 1000}, device_scale_factor=2)
            page.goto(src.as_uri(), wait_until="networkidle")
            page.locator("#chart").screenshot(path=str(out))
            browser.close()

    print(f"Wrote {out.relative_to(REPO_ROOT).as_posix()}  ->  /blog/{Path(args.out).as_posix()}")
    top, bottom = rows[0], rows[-1]
    print(f"Best {top['team']} {top['diff']:+d}, worst {bottom['team']} {bottom['diff']:+d}")


if __name__ == "__main__":
    main()
