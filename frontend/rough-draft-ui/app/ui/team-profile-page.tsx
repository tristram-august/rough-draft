"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  fetchTeamProfile,
  fetchTeamSeasons,
  type TeamGameLogRow,
  type TeamMetric,
} from "../lib/teams";
import { teamColor } from "../lib/team-colors";

// Diverging pair validated for dark mode (dataviz palette check): blue = better half, red = worse half.
const POS = "#3987e5";
const NEG = "#e66767";
const NEUTRAL = "#64748b";

const selectClass =
  "rounded-xl border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs font-medium text-slate-300 outline-none transition-colors focus:border-slate-600";

function ordinal(n: number) {
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 13) return `${n}th`;
  return `${n}${({ 1: "st", 2: "nd", 3: "rd" } as Record<number, string>)[n % 10] ?? "th"}`;
}

function rankLabel(m: TeamMetric) {
  if (m.rank == null) return "";
  return m.better === null ? `${ordinal(m.rank)} highest` : `${ordinal(m.rank)} of ${m.of}`;
}

function percentile(m: TeamMetric) {
  if (m.rank == null || m.of <= 1) return null;
  return (m.of - m.rank) / (m.of - 1);
}

function RankBar({ metric }: { metric: TeamMetric }) {
  const p = percentile(metric);
  if (p == null) return <div className="h-1.5" />;
  const color = metric.better === null ? NEUTRAL : p > 0.5 ? POS : p < 0.5 ? NEG : NEUTRAL;
  return (
    <div className="h-1.5 w-full rounded-full bg-slate-800/80" aria-hidden>
      <div className="h-1.5 rounded-full" style={{ width: `${Math.max(4, p * 100)}%`, background: color }} />
    </div>
  );
}

function SummaryTile({ metric }: { metric: TeamMetric }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
      <div className="text-[11px] font-medium uppercase tracking-wide text-slate-500">{metric.label}</div>
      <div className="mt-1.5 text-2xl font-semibold tabular-nums text-slate-100">{metric.display}</div>
      <div className="mb-2 mt-0.5 text-xs text-slate-400">{rankLabel(metric)}</div>
      <RankBar metric={metric} />
    </div>
  );
}

function MetricCard({ title, metrics }: { title: string; metrics: TeamMetric[] }) {
  return (
    <section className="rounded-3xl border border-slate-800 bg-slate-900/30 p-5">
      <h2 className="mb-4 text-sm font-semibold text-slate-200">{title}</h2>
      <ul className="space-y-3.5">
        {metrics.map((m) => (
          <li key={m.key}>
            <div className="flex items-baseline justify-between gap-3">
              <div className="min-w-0">
                <div className="text-[13px] text-slate-300">{m.label}</div>
                {m.note && <div className="text-[11px] leading-snug text-slate-600">{m.note}</div>}
              </div>
              <div className="shrink-0 text-right">
                <span className="text-sm font-semibold tabular-nums text-slate-100">{m.display}</span>
                <span className="ml-2 inline-block min-w-[4.5rem] text-[11px] tabular-nums text-slate-500">{rankLabel(m)}</span>
              </div>
            </div>
            <div className="mt-1.5">
              <RankBar metric={m} />
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

const fmtEpa = (v: number | null) => (v == null ? "—" : `${v > 0 ? "+" : ""}${v.toFixed(3)}`);

function WeeklyMarginChart({ games }: { games: TeamGameLogRow[] }) {
  const [hover, setHover] = React.useState<number | null>(null);
  const boxRef = React.useRef<HTMLDivElement>(null);
  const [boxWidth, setBoxWidth] = React.useState(900);
  React.useEffect(() => {
    const el = boxRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => setBoxWidth(Math.max(280, Math.round(entry.contentRect.width))));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  const points = games
    .filter((g) => g.off_epa_per_play != null && g.def_epa_per_play_allowed != null)
    .map((g) => ({ ...g, margin: (g.off_epa_per_play as number) - (g.def_epa_per_play_allowed as number) }));
  if (points.length === 0) return null;

  // Drawn at the container's real pixel width so labels stay legible on phones.
  const W = boxWidth;
  const H = 210;
  const padTop = 12;
  const padBottom = 40;
  const plotH = H - padTop - padBottom;
  // Fit the domain to the data (zero always included) so an all-positive season doesn't waste half the plot.
  let hi = Math.max(0, ...points.map((p) => p.margin));
  let lo = Math.min(0, ...points.map((p) => p.margin));
  if (hi - lo < 0.2) {
    if (hi > 0 || lo === 0) hi = lo + 0.2;
    else lo = hi - 0.2;
  }
  const yFor = (v: number) => padTop + ((hi - v) / (hi - lo)) * plotH;
  const zeroY = yFor(0);
  const band = W / points.length;
  const barW = Math.min(44, band * 0.55);
  const active = hover != null ? points[hover] : null;
  const centerPct = hover != null ? ((hover + 0.5) / points.length) * 100 : 0;
  const tooltipStyle: React.CSSProperties =
    centerPct <= 50 ? { left: `calc(${centerPct}% + 32px)` } : { right: `calc(${100 - centerPct}% + 32px)` };

  return (
    <section className="rounded-3xl border border-slate-800 bg-slate-900/30 p-5">
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-sm font-semibold text-slate-200">Weekly EPA/play margin</h2>
        <p className="text-[11px] text-slate-500">Offense EPA/play minus EPA/play allowed. Above the line = outplayed the opponent.</p>
      </div>
      <div className="relative" ref={boxRef}>
        <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} className="block max-w-full" role="img" aria-label="Weekly EPA per play margin">
          <line x1={0} x2={W} y1={zeroY} y2={zeroY} stroke="#334155" strokeWidth={1} />
          {points.map((p, i) => {
            const cx = band * i + band / 2;
            const y = yFor(p.margin);
            const top = Math.min(y, zeroY);
            const h = Math.max(2, Math.abs(y - zeroY));
            const positive = p.margin >= 0;
            return (
              <g key={p.game_id}>
                <rect
                  x={cx - barW / 2}
                  y={top}
                  width={barW}
                  height={h}
                  rx={4}
                  fill={positive ? POS : NEG}
                  opacity={hover == null || hover === i ? 1 : 0.45}
                />
                {(band >= 26 || i % 2 === 0) && (
                  <text x={cx} y={H - 20} textAnchor="middle" fontSize={12} fill="#94a3b8">
                    {p.week != null ? (band >= 26 ? `W${p.week}` : p.week) : ""}
                  </text>
                )}
                {band >= 64 && (
                  <text x={cx} y={H - 5} textAnchor="middle" fontSize={11} fill="#64748b">
                    {p.result ?? ""} {p.opponent ? `${p.home ? "vs" : "@"} ${p.opponent}` : ""}
                  </text>
                )}
                <rect
                  x={band * i}
                  y={0}
                  width={band}
                  height={H}
                  fill="transparent"
                  onMouseEnter={() => setHover(i)}
                  onMouseLeave={() => setHover(null)}
                  onFocus={() => setHover(i)}
                  onBlur={() => setHover(null)}
                  tabIndex={0}
                  aria-label={`Week ${p.week}: margin ${fmtEpa(p.margin)}`}
                />
              </g>
            );
          })}
        </svg>
        {active && hover != null && (
          <div
            className="pointer-events-none absolute top-0 z-10 w-52 rounded-xl border border-slate-700 bg-slate-950/95 px-3 py-2 text-xs shadow-lg"
            style={tooltipStyle}
          >
            <div className="font-semibold text-slate-100">
              Week {active.week} {active.home ? "vs" : "@"} {active.opponent}
            </div>
            <div className="text-slate-400">
              {active.result} {active.points_for}–{active.points_against}
            </div>
            <div className="mt-1 grid grid-cols-2 gap-x-2 tabular-nums text-slate-300">
              <span className="text-slate-500">Offense</span><span className="text-right">{fmtEpa(active.off_epa_per_play)}</span>
              <span className="text-slate-500">Allowed</span><span className="text-right">{fmtEpa(active.def_epa_per_play_allowed)}</span>
              <span className="text-slate-500">Margin</span><span className="text-right font-semibold">{fmtEpa(active.margin)}</span>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

function GameLog({ games, season }: { games: TeamGameLogRow[]; season: number }) {
  return (
    <section className="overflow-x-auto rounded-3xl border border-slate-800">
      <table className="w-full border-collapse text-sm sm:min-w-[720px]">
        <thead className="bg-slate-900/60">
          <tr className="text-xs uppercase tracking-wide text-slate-500">
            <th className="px-3 py-2.5 text-left font-semibold">Wk</th>
            <th className="px-3 py-2.5 text-left font-semibold">Opponent</th>
            <th className="px-3 py-2.5 text-left font-semibold">Result</th>
            <th className="px-2 py-2.5 text-right font-semibold">Off EPA/Play</th>
            <th className="px-2 py-2.5 text-right font-semibold">EPA/Play Allowed</th>
            <th className="px-2 py-2.5 text-right font-semibold">Yards</th>
            <th className="px-2 py-2.5 text-right font-semibold">Yds Allowed</th>
            <th className="px-2 py-2.5 text-right font-semibold">Giveaways</th>
            <th className="px-3 py-2.5 text-right font-semibold">Takeaways</th>
          </tr>
        </thead>
        <tbody>
          {games.map((g) => (
            <tr key={g.game_id} className="border-t border-slate-800/60 transition-colors hover:bg-slate-900/40">
              <td className="px-3 py-2 text-xs tabular-nums text-slate-500">{g.week}</td>
              <td className="px-3 py-2">
                <span className="mr-1.5 text-xs text-slate-600">{g.home ? "vs" : "@"}</span>
                {g.opponent ? (
                  <Link href={`/teams/${g.opponent}?season=${season}`} className="font-medium text-slate-200 hover:text-white hover:underline">
                    {g.opponent}
                  </Link>
                ) : "—"}
              </td>
              <td className="px-3 py-2 text-xs tabular-nums">
                <span className={`mr-1.5 font-semibold ${g.result === "W" ? "text-slate-100" : "text-slate-500"}`}>{g.result ?? "—"}</span>
                <span className="text-slate-400">{g.points_for != null ? `${g.points_for}–${g.points_against}` : ""}</span>
              </td>
              <td className="px-2 py-2 text-right text-xs tabular-nums text-slate-300">{fmtEpa(g.off_epa_per_play)}</td>
              <td className="px-2 py-2 text-right text-xs tabular-nums text-slate-300">{fmtEpa(g.def_epa_per_play_allowed)}</td>
              <td className="px-2 py-2 text-right text-xs tabular-nums text-slate-300">{g.yards}</td>
              <td className="px-2 py-2 text-right text-xs tabular-nums text-slate-300">{g.yards_allowed}</td>
              <td className="px-2 py-2 text-right text-xs tabular-nums text-slate-300">{g.giveaways}</td>
              <td className="px-3 py-2 text-right text-xs tabular-nums text-slate-300">{g.takeaways}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

export function TeamProfilePage({ team, initialSeason }: { team: string; initialSeason: number | null }) {
  const router = useRouter();
  const [season, setSeason] = React.useState<number | null>(initialSeason);
  const seasonsQuery = useQuery({ queryKey: ["team-seasons"], queryFn: fetchTeamSeasons });
  const activeSeason = season ?? seasonsQuery.data?.[0] ?? null;

  const profileQuery = useQuery({
    queryKey: ["team-profile", team, activeSeason],
    queryFn: () => fetchTeamProfile(team, activeSeason as number),
    enabled: activeSeason != null,
    placeholderData: (prev) => prev,
    retry: false,
  });
  const p = profileQuery.data;
  const color = teamColor(team);

  function changeSeason(s: number) {
    setSeason(s);
    router.replace(`/teams/${team}?season=${s}`, { scroll: false });
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <Link href="/teams" className="text-xs text-slate-500 transition-colors hover:text-slate-300">
        ← All teams
      </Link>

      <header className="mt-3 mb-6 overflow-hidden rounded-3xl border border-slate-800 bg-slate-900/40">
        <div className="h-1.5" style={{ background: color }} />
        <div className="flex flex-wrap items-end justify-between gap-4 p-5">
          <div>
            <div className="text-xs font-medium uppercase tracking-[0.16em] text-slate-500">{team}</div>
            <h1 className="mt-1 text-3xl font-semibold text-slate-50">{p?.team_name ?? team}</h1>
            {p && (
              <div className="mt-2 flex flex-wrap items-baseline gap-x-4 gap-y-1 text-sm text-slate-400">
                <span className="text-lg font-semibold tabular-nums text-slate-100">
                  {p.wins}–{p.losses}{p.ties ? `–${p.ties}` : ""}
                </span>
                <span className="tabular-nums">PF {p.points_for}</span>
                <span className="tabular-nums">PA {p.points_against}</span>
                <span className="tabular-nums">{p.games} games</span>
              </div>
            )}
          </div>
          <select
            aria-label="Season"
            value={activeSeason ?? ""}
            onChange={(e) => changeSeason(Number(e.target.value))}
            className={selectClass}
          >
            {(seasonsQuery.data ?? []).map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
      </header>

      {profileQuery.isError && (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 px-4 py-3 text-sm text-slate-400">
          No {team} regular-season games found for {activeSeason}.
        </div>
      )}
      {profileQuery.isLoading && <p className="text-sm text-slate-500">Loading…</p>}

      {p && !profileQuery.isError && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            {p.summary.map((m) => <SummaryTile key={m.key} metric={m} />)}
          </div>

          <WeeklyMarginChart games={p.game_log} />

          <GameLog games={p.game_log} season={p.season} />

          <p className="text-xs leading-relaxed text-slate-500">
            Ranks are against all {p.summary[0]?.of ?? 32} teams this season. Bars run longer for better ranks — blue in the
            top half of the league, red in the bottom half. Gray bars are style stats (pass rate, depth of target) ranked
            highest to lowest, not good or bad.
          </p>

          <div className="grid gap-4 lg:grid-cols-3">
            <MetricCard title="Offense" metrics={p.offense} />
            <MetricCard title="Defense" metrics={p.defense} />
            <MetricCard title="Special teams & discipline" metrics={p.special_teams} />
          </div>

          <p className="text-xs leading-relaxed text-slate-600">
            Source: nflverse team box scores. EPA/play counts pass attempts and carries; yards/play also counts sacks.
            Defensive numbers are what opponents gained against this team.
          </p>
        </div>
      )}
    </div>
  );
}
