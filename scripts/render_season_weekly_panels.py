"""
Week-by-week breakdown blog panels for the season round-up: the season's top
Outperformed / Underperformed / Closest-to-Projection players, one diverging
bar per week (diff vs. projection) with that week's actual PPR score.

    python scripts/render_season_weekly_panels.py --min-projected 60

Needs the API running. Writes season_over_weekly.png, season_under_weekly.png
and season_closest_weekly.png to --out-dir (default output/social/season_panels_week_<N>/).
"""
from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

TOP = 6

TEMPLATE = """<!doctype html><html><head><meta charset="utf-8"><style>
:root{--bg:#0d1117;--surface:#141a22;--surface-2:#1a212b;--border:#262e39;--text:#e6e8eb;--muted:#8b94a3;--faint:#5f6b7d;
--pos:#3987e5;--neg:#e66767;--zero:#525b68}
*{box-sizing:border-box}body{margin:0;background:var(--bg)}
.panel{width:540px;background:var(--surface);border:1px solid var(--border);border-radius:14px;overflow:hidden;
font-family:"IBM Plex Sans",-apple-system,"Segoe UI",sans-serif;color:var(--text)}
.head{display:flex;align-items:center;gap:8px;padding:13px 16px;border-bottom:1px solid var(--border);background:var(--surface-2)}
.head .dot{width:8px;height:8px;border-radius:50%}.head h3{font-size:13px;margin:0;font-weight:650}
.head .period{margin-left:auto;font-size:10.5px;color:var(--faint);font-family:"IBM Plex Mono",monospace}
.sub{padding:12px 16px 0;margin:0;font-size:11px;color:var(--muted);line-height:1.5}
.legend{display:flex;gap:14px;align-items:center;padding:10px 16px 2px;flex-wrap:wrap;font-size:10px;color:var(--muted)}
.legend .sw{display:inline-block;width:8px;height:8px;border-radius:2px;margin-right:5px;vertical-align:-1px}
.grid{display:grid;grid-template-columns:104px 1fr 52px;align-items:center}
.heads{padding:10px 16px 4px;font-family:"IBM Plex Mono",monospace;font-size:9px;letter-spacing:.05em;text-transform:uppercase;color:var(--faint)}
.heads .wk{display:flex;justify-content:space-around}.r{text-align:right}
.rows{padding:2px 6px 8px}.row{padding:8px 10px}
.who{display:flex;align-items:center;min-width:0}
.badge{flex:none;font-size:9.5px;font-weight:700;padding:1.5px 5px;border-radius:4px;margin-right:6px;background:#1e232b;color:#9aa5b4}
.badge.RB{background:#123326;color:#4fe0a0}.badge.TE{background:#3a2c14;color:#f0b95c}.badge.QB{background:#3a2440;color:#d89ff0}.badge.WR{background:#122f3a;color:#5cc3ef}
.name{font-size:12px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}
.weeks{display:flex;justify-content:space-around;height:104px;position:relative}
.row .weeks::before{content:"";position:absolute;left:2px;right:2px;top:52px;height:1px;background:var(--zero)}
.wb{flex:1;position:relative}
.bar{width:10px;position:absolute;left:50%;transform:translateX(-50%)}
.bar.pos{background:var(--pos);bottom:52px;border-radius:3px 3px 0 0}.bar.neg{background:var(--neg);top:52px;border-radius:0 0 3px 3px}
.lbl{position:absolute;left:50%;transform:translateX(-50%);text-align:center;white-space:nowrap;font-family:"IBM Plex Mono",monospace}
.lbl .d{display:block;font-size:8px;font-weight:700}.lbl .s{display:block;font-size:7px;color:var(--faint);margin-top:1px}
.lbl.pos .d{color:var(--pos)}.lbl.neg .d{color:var(--neg)}
.dnp{position:absolute;left:50%;top:52px;transform:translate(-50%,-50%);font-size:12px;font-weight:700;color:var(--muted);font-family:"IBM Plex Mono",monospace;background:var(--surface);padding:0 3px;line-height:1}
.total{text-align:right;font-family:"IBM Plex Mono",monospace;font-size:14px;font-weight:700}
.total.pos{color:var(--pos)}.total.neg{color:var(--neg)}.total.zero{color:var(--zero)}
footer{padding:10px 16px 14px;font-size:9.5px;color:var(--faint);line-height:1.5;border-top:1px solid var(--border)}
</style></head><body><div class="panel" id="chart"></div><script>
const CFG = __CFG__;
const fmt = n => (Math.abs(n) < 0.05 ? "0.0" : (n > 0 ? "+" : "\\u2212") + Math.abs(n).toFixed(1));
const vals = CFG.rows.flatMap(r => r.weeks.filter(Boolean).map(w => Math.abs(w.diff)));
// Baseline sits 52px down; bars top out 22px short of the edge so the two-line label always fits inside the row.
const MAX = Math.max(1, ...vals), BASE = 52, ROOM = BASE - 22;
function bar(w) {
  if (!w) return `<div class="wb"><span class="dnp" title="Didn't play (bye or out)">\\u2014</span></div>`;
  const h = Math.max(2, Math.round(Math.abs(w.diff) / MAX * ROOM)), s = w.diff >= 0 ? "pos" : "neg";
  const pos = s === "pos" ? `bottom:${BASE + h + 3}px` : `top:${BASE + h + 3}px`;
  return `<div class="wb"><div class="bar ${s}" style="height:${h}px"></div>
    <div class="lbl ${s}" style="${pos}"><span class="d">${fmt(w.diff)}</span><span class="s">${w.actual.toFixed(1)}p</span></div></div>`;
}
const weekHeads = CFG.weeks.map(w => `<span>W${w}</span>`).join("");
document.getElementById("chart").innerHTML = `
  <div class="head"><span class="dot" style="background:${CFG.dot}"></span><h3>${CFG.title}</h3><span class="period">${CFG.period}</span></div>
  <p class="sub">${CFG.sub}</p>
  <div class="legend"><span><span class="sw" style="background:var(--pos)"></span>Beat that week</span>
    <span><span class="sw" style="background:var(--neg)"></span>Missed that week</span><span style="color:var(--faint)">small number = PPR points scored · \\u2014 = didn't play</span></div>
  <div class="grid heads"><span>Player</span><div class="wk">${weekHeads}</div><span class="r">Season</span></div>
  <div class="rows">${CFG.rows.map(r => {
    const cls = Math.abs(r.season) < 0.5 ? "zero" : r.season > 0 ? "pos" : "neg";
    return `<div class="grid row"><div class="who"><span class="badge ${r.pos}">${r.pos}</span><span class="name" title="${r.name}">${r.name}</span></div>
      <div class="weeks">${r.weeks.map(bar).join("")}</div><div class="total ${cls}">${fmt(r.season)}</div></div>`;
  }).join("")}</div>
  <footer>${CFG.foot}</footer>`;
</script></body></html>"""


def get(api: str, path: str):
    return json.load(urllib.request.urlopen(f"{api}{path}"))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--season", type=int, default=2026)
    p.add_argument("--min-projected", type=float, default=60.0, help="Season projection floor for Closest to Projection.")
    p.add_argument("--api-url", default="http://localhost:8000/api")
    p.add_argument("--out-dir", default=None)
    args = p.parse_args()

    total = get(args.api_url, f"/fantasy/projection-diff?season={args.season}&scoring=ppr")
    weeks = total["weeks"]
    rows = [r for r in total["rows"] if r["position"] not in ("K", "DST")]
    lists = {
        "over": sorted(rows, key=lambda r: -r["diff"])[:TOP],
        "under": sorted(rows, key=lambda r: r["diff"])[:TOP],
        "closest": sorted((r for r in rows if r["projected"] >= args.min_projected), key=lambda r: abs(r["diff"]))[:TOP],
    }
    by_week = {
        w: {r["gsis_id"]: r for r in get(args.api_url, f"/fantasy/projection-diff?season={args.season}&week={w}&scoring=ppr")["rows"]}
        for w in weeks
    }
    period = f"Weeks {weeks[0]}–{weeks[-1]}"
    meta = {
        "over": ("Outperformed, Week by Week", "#3987e5", "The season's biggest beats so far, broken out by week instead of just the total."),
        "under": ("Underperformed, Week by Week", "#e66767", "The season's biggest busts so far, broken out by week instead of just the total."),
        "closest": ("Closest to Projection, Week by Week", "#e8a33d",
                    f"The most accurate season projections (players projected {args.min_projected:.0f}+ points) — even those swing week to week."),
    }
    out = Path(args.out_dir or f"output/social/season_panels_week_{weeks[-1]}")
    out.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for kind, players in lists.items():
            # Fresh page per panel: the template declares page-level constants.
            page = browser.new_page(viewport={"width": 700, "height": 1000}, device_scale_factor=2)
            errors: list[str] = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            title, dot, sub = meta[kind]
            cfg = {
                "title": title, "dot": dot, "sub": sub, "period": period, "weeks": weeks,
                "foot": "Bar height = points above/below that week's FantasyPros projection (PPR). Projections: FantasyPros.",
                "rows": [
                    {
                        "name": r["name"], "pos": r["position"], "season": r["diff"],
                        "weeks": [
                            ({"diff": by_week[w][r["gsis_id"]]["diff"], "actual": by_week[w][r["gsis_id"]]["actual"]}
                             if r["gsis_id"] in by_week[w] else None)
                            for w in weeks
                        ],
                    }
                    for r in players
                ],
            }
            page.set_content(TEMPLATE.replace("__CFG__", json.dumps(cfg)), wait_until="networkidle")
            if errors:
                raise SystemExit(f"{kind} panel failed to render: {errors}")
            path = out / f"season_{kind}_weekly.png"
            page.locator("#chart").screenshot(path=str(path))
            page.close()
            print(f"wrote {path}")
        browser.close()


if __name__ == "__main__":
    main()
