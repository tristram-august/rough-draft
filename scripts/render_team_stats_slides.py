"""
Instagram carousel (1080x1350 @2x) for the team-stats blog images: points
scored, points allowed, point differential and turnover margin.

    python scripts/render_team_stats_slides.py              # after the latest week, 2026
    python scripts/render_team_stats_slides.py --week 9     # label + output folder for week 9

Reads the production API (same numbers as /teams and the blog panels in
public/blog/team-stats/). Writes output/social/team_stats_week_<N>/01_cover.png
... 06_cta.png.

Same look as the /social/playoffs carousel (render_playoff_slides.py): brand
bar, IBM Plex, #0d1117 frame, #141a22 cards, team-color ticks. 32 rows are
unreadable on a phone at this size, so ranking slides show the top and bottom
of the league; bars are always scaled against all 32 teams so lengths stay
honest. Bars carry color; numbers stay in text ink.
"""
from __future__ import annotations

import argparse
import html
import json
import tempfile
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parents[1]
PROD_API = "https://rough-draft-production.up.railway.app/api"

TEAM_COLORS = {  # frontend/rough-draft-ui/app/lib/team-colors.ts
    "ARI": "#97233F", "ATL": "#A71930", "BAL": "#241773", "BUF": "#00338D", "CAR": "#0085CA", "CHI": "#C83803",
    "CIN": "#FB4F14", "CLE": "#FF3C00", "DAL": "#003594", "DEN": "#FB4F14", "DET": "#0076B6", "GB": "#203731",
    "HOU": "#C60C30", "IND": "#002C5F", "JAX": "#006778", "KC": "#E31837", "LAC": "#0080C6", "LAR": "#003594",
    "LV": "#A5ACAF", "MIA": "#008E97", "MIN": "#4F2683", "NE": "#002244", "NO": "#9F8958", "NYG": "#0B2265",
    "NYJ": "#125740", "PHI": "#004C54", "PIT": "#FFB612", "SEA": "#69BE28", "SF": "#AA0000", "TB": "#D50A0A",
    "TEN": "#4B92DB", "WAS": "#5A1414",
}

CSS = """
*{box-sizing:border-box}body{margin:0;background:#0d1117}
.frame{width:1080px;height:1350px;background:#0d1117;color:#e6e8eb;font-family:"IBM Plex Sans",sans-serif;
  display:flex;flex-direction:column;padding:72px 76px;position:relative;overflow:hidden}
.mono{font-family:"IBM Plex Mono",monospace}
.brand{display:flex;justify-content:space-between;align-items:center}
.brand .l{font-family:"IBM Plex Mono",monospace;font-size:22px;letter-spacing:.14em;color:#e8a33d;font-weight:600}
.brand .r{font-family:"IBM Plex Mono",monospace;font-size:20px;color:#5f6b7d;text-transform:uppercase}
.foot{position:absolute;left:76px;right:76px;bottom:56px;display:flex;justify-content:space-between;
  font-family:"IBM Plex Mono",monospace;font-size:18px;color:#5f6b7d}
.kicker{font-family:"IBM Plex Mono",monospace;font-size:24px;letter-spacing:.1em;color:#e8a33d;margin-bottom:18px}
h1{font-size:96px;font-weight:700;line-height:1.02;letter-spacing:-.01em;margin:0}
h2{font-size:64px;font-weight:700;line-height:1.05;letter-spacing:-.01em;margin:58px 0 0}
.sub{margin-top:18px;font-size:26px;color:#93a0b3}
.card{padding:26px 28px;border-radius:20px;background:#141a22;border:1px solid #262e39}
.card .lab{font-size:20px;color:#93a0b3}
.card .who{display:flex;align-items:center;gap:14px;margin-top:12px}
.tick{flex:none;width:8px;border-radius:4px}
.card .nm{font-size:34px;font-weight:650}
.card .big{margin-left:auto;font-family:"IBM Plex Mono",monospace;font-size:44px;font-weight:700}
.card .val{margin-top:14px;font-family:"IBM Plex Mono",monospace;font-size:40px;font-weight:700}
.card .s{margin-top:4px;font-size:19px;color:#5f6b7d}
.list{margin-top:40px}
.row{display:grid;grid-template-columns:46px 8px 300px 1fr 96px;column-gap:16px;align-items:center;height:46px;margin-top:4px}
.rk{font-family:"IBM Plex Mono",monospace;font-size:20px;color:#5f6b7d;text-align:right}
.row .nm{font-size:27px;font-weight:600;white-space:nowrap}
.track{position:relative;height:100%}
.bar{position:absolute;top:12px;height:22px}
.bar.one{left:0;background:#3987e5;border-radius:0 4px 4px 0}
.bar.pos{left:50%;background:#3987e5;border-radius:0 4px 4px 0}
.bar.neg{right:50%;background:#e66767;border-radius:4px 0 0 4px}
.track.div::before{content:"";position:absolute;left:50%;top:-4px;bottom:-4px;width:2px;margin-left:-1px;background:#525b68}
.v{font-family:"IBM Plex Mono",monospace;font-size:28px;font-weight:700;text-align:right}
.gap{height:34px;display:flex;align-items:center;justify-content:center;font-family:"IBM Plex Mono",monospace;
  font-size:20px;letter-spacing:.3em;color:#5f6b7d}
.legend{display:flex;gap:28px;margin-top:22px;font-size:21px;color:#93a0b3}
.legend i{display:inline-block;width:16px;height:16px;border-radius:4px;margin-right:10px;vertical-align:-2px}
.pill{display:inline-block;margin-top:44px;padding:22px 30px;border-radius:999px;background:#1c160b;border:1px solid #3b2d12;
  font-family:"IBM Plex Mono",monospace;font-size:40px;color:#e8a33d}
"""

PAGE = """<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&family=IBM+Plex+Sans:wght@400;500;600;700&display=block" rel="stylesheet">
<style>__CSS__</style></head><body>__BODY__</body></html>"""

esc = html.escape


def sgn(n: int) -> str:
    return f"+{n}" if n > 0 else f"−{abs(n)}" if n < 0 else "0"


def frame(right: str, body: str, foot_right: str) -> str:
    return (f'<div class="frame"><div class="brand"><span class="l">ROUGH DRAFT FOOTBALL</span>'
            f'<span class="r">{esc(right)}</span></div>{body}'
            f'<div class="foot"><span>roughdraftfootball.com</span><span>{esc(foot_right)}</span></div></div>')


def tick(team: str, h: int = 40) -> str:
    return f'<span class="tick" style="height:{h}px;background:{TEAM_COLORS.get(team, "#475569")}"></span>'


def ranked_rows(rows: list[dict], key: str, top: int, bottom: int, diverging: bool) -> str:
    """rows are already in display order (rank 1 first)."""
    lim = max(abs(r[key]) for r in rows) or 1
    picks = list(enumerate(rows[:top], 1)) + [None] + list(enumerate(rows[-bottom:], len(rows) - bottom + 1))
    out = []
    for item in picks:
        if item is None:
            out.append('<div class="gap">···</div>')
            continue
        rank, r = item
        v = r[key]
        if diverging:
            cls = "pos" if v > 0 else "neg" if v < 0 else ""
            bar = f'<div class="bar {cls}" style="width:{abs(v) / lim * 50:.2f}%"></div>' if cls else ""
            track, label = f'<div class="track div">{bar}</div>', sgn(v)
        else:
            track = f'<div class="track"><div class="bar one" style="width:{v / lim * 100:.2f}%"></div></div>'
            label = str(v)
        out.append(f'<div class="row"><span class="rk">{rank}</span>{tick(r["team"])}'
                   f'<span class="nm">{esc(r["team_name"])}</span>{track}<span class="v">{label}</span></div>')
    return '<div class="list">' + "".join(out) + "</div>"


def build_slides(rows: list[dict], season: int, week: int) -> list[tuple[str, str]]:
    period = f"{season} · After Week {week}"
    foot = f"nflverse · {season} regular season"
    for r in rows:
        r["diff"] = r["points_for"] - r["points_against"]

    by_pf = sorted(rows, key=lambda r: (-r["points_for"], r["team_name"]))
    by_pa = sorted(rows, key=lambda r: (r["points_against"], r["team_name"]))
    by_diff = sorted(rows, key=lambda r: (-r["diff"], -r["diff"] / r["games"], r["team_name"]))
    by_to = sorted(rows, key=lambda r: (-r["turnover_margin"], -r["turnover_margin"] / r["games"],
                                        -r["takeaways"], r["team_name"]))

    best, off, dfn, to = by_diff[0], by_pf[0], by_pa[0], by_to[0]
    tied_to = [r for r in by_to if r["turnover_margin"] == to["turnover_margin"]]

    def small(label: str, r: dict, value: str, sub: str) -> str:
        return (f'<div class="card" style="flex:1"><div class="lab">{label}</div><div class="who">{tick(r["team"])}'
                f'<span class="nm">{esc(r["team_name"])}</span></div><div class="val">{value}</div>'
                f'<div class="s">{sub}</div></div>')

    cover = frame(period, f"""
      <div style="flex:1;display:flex;flex-direction:column;justify-content:center">
        <div class="kicker">TEAM STATS</div>
        <h1>Winning the<br>Margins</h1>
        <div class="sub">Scoring, defense and turnovers for all 32 teams · After Week {week}</div>
        <div class="card" style="margin-top:52px"><div class="lab">Best point differential</div>
          <div class="who">{tick(best["team"])}<span class="nm" style="font-size:38px">{esc(best["team_name"])}</span>
          <span class="big">{sgn(best["diff"])}</span></div></div>
        <div style="display:flex;gap:22px;margin-top:22px">
          {small("Most points scored", off, str(off["points_for"]), f'{off["points_for"] / off["games"]:.1f} per game')}
          {small("Fewest points allowed", dfn, str(dfn["points_against"]), f'{dfn["points_against"] / dfn["games"]:.1f} per game')}
        </div>
      </div>""", foot)

    def ranking(title: str, sub: str, body: str, legend: str = "") -> str:
        return frame(period, f'<h2>{title}</h2><div class="sub">{sub}</div>{legend}{body}', foot)

    legend_pd = ('<div class="legend"><span><i style="background:#3987e5"></i>Outscoring opponents</span>'
                 '<span><i style="background:#e66767"></i>Being outscored</span></div>')
    legend_to = ('<div class="legend"><span><i style="background:#3987e5"></i>More takeaways</span>'
                 '<span><i style="background:#e66767"></i>More giveaways</span></div>')
    to_sub = "Takeaways minus giveaways · top 8 and bottom 8"
    if len(tied_to) > 1:
        to_sub = f"Takeaways minus giveaways · {len(tied_to)} teams tied for the lead at {sgn(to['turnover_margin'])}"

    slides = [
        ("01_cover", cover),
        ("02_points_scored", ranking("Points Scored", "Total points · top 10 and bottom 5 offenses",
                                     ranked_rows(by_pf, "points_for", 10, 5, False))),
        ("03_points_allowed", ranking("Fewest Points Allowed", "Total points allowed · top 10 and bottom 5 defenses",
                                      ranked_rows(by_pa, "points_against", 10, 5, False))),
        ("04_point_differential", ranking("Point Differential", "Points scored minus points allowed · top 8 and bottom 8",
                                          ranked_rows(by_diff, "diff", 8, 8, True), legend_pd)),
        ("05_turnover_margin", ranking("Turnover Margin", to_sub, ranked_rows(by_to, "turnover_margin", 8, 8, True), legend_to)),
        ("06_cta", frame(period, """
          <div style="flex:1;display:flex;flex-direction:column;justify-content:center">
            <h1 style="font-size:80px">Every team's stats,<br>updated weekly</h1>
            <div class="sub">Offense, defense, EPA and turnovers for all 32 teams — link in bio</div>
            <div><span class="pill">roughdraftfootball.com/teams</span></div>
          </div>""", foot)),
    ]
    return slides


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--season", type=int, default=2026)
    p.add_argument("--week", type=int, default=None, help="Label/folder week (defaults to the max games played).")
    p.add_argument("--api-url", default=PROD_API)
    p.add_argument("--out-dir", default=None)
    args = p.parse_args()

    url = f"{args.api_url}/teams/stats?season={args.season}&sort=points_for&direction=desc"
    rows = [r for r in json.load(urllib.request.urlopen(url, timeout=30))["rows"] if r["games"]]
    week = args.week or max(r["games"] for r in rows)
    out_dir = Path(args.out_dir) if args.out_dir else REPO_ROOT / "output" / "social" / f"team_stats_week_{week}"
    out_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=2)
        for name, body in build_slides(rows, args.season, week):
            src = Path(tmp) / f"{name}.html"
            src.write_text(PAGE.replace("__CSS__", CSS).replace("__BODY__", body), encoding="utf-8")
            page.goto(src.as_uri(), wait_until="networkidle")
            page.evaluate("document.fonts.ready")
            path = out_dir / f"{name}.png"
            page.locator(".frame").screenshot(path=str(path))
            print(f"OK   {path.relative_to(REPO_ROOT).as_posix()}")
        browser.close()


if __name__ == "__main__":
    main()
