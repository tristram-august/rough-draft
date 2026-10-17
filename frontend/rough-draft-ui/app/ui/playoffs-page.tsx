"use client";

import * as React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "./page-header";
import { Segmented } from "./segmented";
import { teamColor } from "../lib/team-colors";
import {
  fetchPlayoffCalibration,
  fetchPlayoffOdds,
  fmtProb,
  fmtRecord,
  type PlayoffTeamOdds,
} from "../lib/playoffs";

type Conference = "AFC" | "NFC";

// Validated categorical slots 1-4 for dark mode (dataviz palette check).
const SERIES = ["#3987e5", "#d95926", "#199e70", "#c98500"];
const DIVISIONS = ["East", "North", "South", "West"];

const selectClass =
  "rounded-xl border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs font-medium text-slate-300 outline-none transition-colors focus:border-slate-600";

const weekLabel = (w: number) => (w === 0 ? "Preseason" : `After week ${w}`);

function ProbCell({ p, strong = false }: { p: number; strong?: boolean }) {
  return (
    <td className="px-1 py-1">
      <div
        className={`rounded-md px-2 py-1.5 text-right text-xs tabular-nums ${strong ? "font-semibold text-slate-50" : "text-slate-200"}`}
        style={{ background: `rgba(57, 135, 229, ${(p * 0.5).toFixed(3)})` }}
      >
        {fmtProb(p)}
      </div>
    </td>
  );
}

function Sparkline({ points }: { points: number[] }) {
  const W = 76;
  const H = 22;
  if (points.length < 2) return <span className="text-[11px] text-slate-600">—</span>;
  const x = (i: number) => 2 + (i / (points.length - 1)) * (W - 4);
  const y = (p: number) => 2 + (1 - p) * (H - 4);
  const d = points.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p).toFixed(1)}`).join(" ");
  const last = points[points.length - 1];
  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} aria-hidden className="inline-block align-middle">
      <line x1={0} x2={W} y1={y(0.5)} y2={y(0.5)} stroke="#1e293b" strokeDasharray="2 2" />
      <path d={d} fill="none" stroke="#94a3b8" strokeWidth={1.5} strokeLinejoin="round" />
      <circle cx={x(points.length - 1)} cy={y(last)} r={2.5} fill="#e2e8f0" />
    </svg>
  );
}

function OddsTable({ teams }: { teams: PlayoffTeamOdds[] }) {
  return (
    <div className="overflow-x-auto rounded-3xl border border-slate-800">
      <table className="w-full border-collapse text-sm sm:min-w-[820px]">
        <thead className="bg-slate-900/60">
          <tr className="text-[11px] uppercase tracking-wide text-slate-500">
            <th className="px-3 py-2.5 text-left font-semibold">Team</th>
            <th className="px-2 py-2.5 text-right font-semibold">Record</th>
            <th className="px-2 py-2.5 text-right font-semibold" title="Average final regular-season wins across simulations">Proj. W</th>
            <th className="px-2 py-2.5 text-right font-semibold">Playoffs</th>
            <th className="px-2 py-2.5 text-right font-semibold">Win Div</th>
            <th className="px-2 py-2.5 text-right font-semibold" title="Earn the 1 seed and the only first-round bye">Bye</th>
            <th className="px-2 py-2.5 text-right font-semibold">Win Conf</th>
            <th className="px-2 py-2.5 text-right font-semibold">Win SB</th>
            <th className="px-3 py-2.5 text-left font-semibold">Playoff odds trend</th>
          </tr>
        </thead>
        <tbody>
          {teams.map((t, i) => (
            <tr
              key={t.team}
              className={`transition-colors hover:bg-slate-900/40 ${i === 7 ? "border-t-2 border-dashed border-slate-700" : "border-t border-slate-800/60"}`}
            >
              <td className="px-3 py-1.5">
                <div className="flex items-center gap-2">
                  <span className="h-6 w-1 shrink-0 rounded-full" style={{ background: teamColor(t.team) }} />
                  <Link href={`/teams/${t.team}`} className="font-medium text-slate-100 hover:text-white hover:underline">
                    {t.team_name ?? t.team}
                  </Link>
                  <span className="text-[11px] text-slate-600">{t.division}</span>
                </div>
              </td>
              <td className="px-2 py-1.5 text-right text-xs tabular-nums text-slate-300">{fmtRecord(t.wins, t.losses)}</td>
              <td className="px-2 py-1.5 text-right text-xs tabular-nums text-slate-400">{t.mean_wins.toFixed(1)}</td>
              <ProbCell p={t.make_playoffs} strong />
              <ProbCell p={t.win_division} />
              <ProbCell p={t.first_seed} />
              <ProbCell p={t.win_conference} />
              <ProbCell p={t.win_super_bowl} />
              <td className="px-3 py-1.5">
                <Sparkline points={t.history.map((h) => h.make_playoffs)} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DivisionChart({ title, teams, weeks }: { title: string; teams: PlayoffTeamOdds[]; weeks: number[] }) {
  const [hover, setHover] = React.useState<number | null>(null);
  const boxRef = React.useRef<HTMLDivElement>(null);
  const [boxWidth, setBoxWidth] = React.useState(420);
  React.useEffect(() => {
    const el = boxRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => setBoxWidth(Math.max(260, Math.round(entry.contentRect.width))));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  // Drawn at the card's real pixel width so axis text stays legible on phones.
  const W = boxWidth;
  const H = 190;
  const padL = 34;
  const padR = 52;
  const padT = 10;
  const padB = 24;
  const n = weeks.length;
  const x = (i: number) => padL + (n > 1 ? (i / (n - 1)) * (W - padL - padR) : (W - padL - padR) / 2);
  const y = (p: number) => padT + (1 - p) * (H - padT - padB);
  // Fixed alphabetical order so a team keeps its color no matter how the race shifts.
  const ordered = [...teams].sort((a, b) => a.team.localeCompare(b.team));
  const valueAt = (t: PlayoffTeamOdds, i: number) => t.history.find((h) => h.week === weeks[i])?.make_playoffs ?? null;

  // Nudge end labels apart so close finishes don't overprint.
  const ends = ordered
    .map((t, k) => ({ t, k, y: y(valueAt(t, n - 1) ?? 0) }))
    .sort((a, b) => a.y - b.y);
  for (let i = 1; i < ends.length; i++) ends[i].y = Math.max(ends[i].y, ends[i - 1].y + 12);
  const overflow = ends.length ? ends[ends.length - 1].y - (H - padB) : 0;
  if (overflow > 0) ends.forEach((e) => (e.y -= overflow));

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/30 p-4">
      <div className="mb-1 text-xs font-semibold text-slate-300">{title}</div>
      <div className="relative" ref={boxRef}>
        <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} className="block max-w-full" role="img" aria-label={`${title} playoff odds by week`}>
          {[0, 0.5, 1].map((p) => (
            <g key={p}>
              <line x1={padL} x2={W - padR} y1={y(p)} y2={y(p)} stroke="#1e293b" strokeWidth={1} />
              <text x={padL - 6} y={y(p) + 3.5} textAnchor="end" fontSize={10} fill="#64748b">{p * 100}%</text>
            </g>
          ))}
          {weeks.map((w, i) => (
            ((W - padL - padR) / Math.max(1, n - 1) >= 22 || i % 2 === 0 || i === n - 1) && (
              <text key={w} x={x(i)} y={H - 6} textAnchor="middle" fontSize={10} fill="#64748b">{w === 0 ? "Pre" : w}</text>
            )
          ))}
          {hover != null && <line x1={x(hover)} x2={x(hover)} y1={padT} y2={H - padB} stroke="#475569" strokeWidth={1} />}
          {ordered.map((t, k) => {
            const pts = weeks.map((_, i) => valueAt(t, i)).map((v, i) => (v == null ? null : [x(i), y(v)] as const));
            const d = pts.filter(Boolean).map((p, i) => `${i ? "L" : "M"}${p![0].toFixed(1)},${p![1].toFixed(1)}`).join(" ");
            const last = pts[pts.length - 1];
            return (
              <g key={t.team}>
                <path d={d} fill="none" stroke={SERIES[k]} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
                {last && <circle cx={last[0]} cy={last[1]} r={4} fill={SERIES[k]} stroke="#0b1120" strokeWidth={2} />}
                {hover != null && pts[hover] && <circle cx={pts[hover]![0]} cy={pts[hover]![1]} r={4} fill={SERIES[k]} stroke="#0b1120" strokeWidth={2} />}
              </g>
            );
          })}
          {ends.map(({ t, k, y: ly }) => (
            <g key={t.team}>
              <rect x={W - padR + 8} y={ly - 4} width={8} height={8} rx={2} fill={SERIES[k]} />
              <text x={W - padR + 20} y={ly + 3.5} fontSize={11} fill="#cbd5e1">{t.team}</text>
            </g>
          ))}
          {weeks.map((w, i) => (
            <rect
              key={w}
              x={x(i) - (W - padL - padR) / Math.max(1, n - 1) / 2}
              y={0}
              width={(W - padL - padR) / Math.max(1, n - 1)}
              height={H}
              fill="transparent"
              onMouseEnter={() => setHover(i)}
              onMouseLeave={() => setHover(null)}
            />
          ))}
        </svg>
        {hover != null && (
          <div
            className="pointer-events-none absolute top-0 z-10 w-40 rounded-xl border border-slate-700 bg-slate-950/95 px-3 py-2 text-xs shadow-lg"
            style={hover / Math.max(1, n - 1) < 0.5 ? { left: `${(x(hover) / W) * 100 + 4}%` } : { right: `${100 - (x(hover) / W) * 100 + 4}%` }}
          >
            <div className="mb-1 font-semibold text-slate-200">{weekLabel(weeks[hover])}</div>
            {[...ordered]
              .map((t) => ({ t, v: valueAt(t, hover), k: ordered.indexOf(t) }))
              .sort((a, b) => (b.v ?? 0) - (a.v ?? 0))
              .map(({ t, v, k }) => (
                <div key={t.team} className="flex items-center justify-between gap-2 tabular-nums">
                  <span className="flex items-center gap-1.5 text-slate-300">
                    <span className="h-2 w-2 rounded-sm" style={{ background: SERIES[k] }} />
                    {t.team}
                  </span>
                  <span className="text-slate-100">{v == null ? "—" : fmtProb(v)}</span>
                </div>
              ))}
          </div>
        )}
      </div>
    </div>
  );
}

function Calibration() {
  const q = useQuery({ queryKey: ["playoff-calibration"], queryFn: fetchPlayoffCalibration });
  const rows = q.data?.rows ?? [];
  if (!rows.length) return null;
  return (
    <section className="rounded-3xl border border-slate-800 bg-slate-900/30 p-5">
      <h2 className="text-sm font-semibold text-slate-200">How accurate are these odds?</h2>
      <p className="mt-1 max-w-2xl text-xs leading-relaxed text-slate-500">
        We re-ran the model as of every week of the {q.data?.seasons} seasons — years it never saw while being tuned — and
        checked who actually made the playoffs. If the odds are honest, teams given about 30% should make it about 30% of
        the time.
      </p>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full max-w-xl border-collapse text-sm">
          <thead>
            <tr className="text-[11px] uppercase tracking-wide text-slate-500">
              <th className="py-2 pr-3 text-left font-semibold">When the model said</th>
              <th className="px-3 py-2 text-right font-semibold">Average odds</th>
              <th className="px-3 py-2 text-right font-semibold">Actually made it</th>
              <th className="px-3 py-2 text-right font-semibold">Team-weeks</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.bucket_lo} className="border-t border-slate-800/60">
                <td className="py-1.5 pr-3 text-xs text-slate-400">
                  {Math.round(r.bucket_lo * 100)}–{Math.round(r.bucket_hi * 100)}%
                </td>
                <td className="px-3 py-1.5 text-right text-xs tabular-nums text-slate-300">{(r.predicted * 100).toFixed(1)}%</td>
                <td className="px-3 py-1.5 text-right text-xs font-semibold tabular-nums text-slate-100">{(r.actual * 100).toFixed(1)}%</td>
                <td className="px-3 py-1.5 text-right text-xs tabular-nums text-slate-500">{r.n.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export function PlayoffsPage() {
  const [conference, setConference] = React.useState<Conference>("AFC");
  const [week, setWeek] = React.useState<number | null>(null);
  const q = useQuery({
    queryKey: ["playoff-odds", week],
    queryFn: () => fetchPlayoffOdds(week),
    placeholderData: (prev) => prev,
  });
  const data = q.data;
  const confTeams = (data?.teams ?? []).filter((t) => t.conference === conference);
  const shownWeeks = (data?.weeks ?? []).filter((w) => w <= (data?.week ?? 0));

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <PageHeader
        eyebrow="Playoffs"
        title="Playoff Odds"
        subtitle="Every team's chances, from 10,000 simulations of the rest of the season using the site's Elo ratings. Updated after each week's games."
      />

      <div className="mb-5 flex flex-wrap items-center gap-2">
        <Segmented
          ariaLabel="Conference"
          value={conference}
          onChange={(v) => setConference(v as Conference)}
          options={[{ value: "AFC", label: "AFC" }, { value: "NFC", label: "NFC" }]}
        />
        <select
          aria-label="Week"
          value={week ?? ""}
          onChange={(e) => setWeek(e.target.value === "" ? null : Number(e.target.value))}
          className={selectClass}
        >
          <option value="">Latest</option>
          {[...(data?.weeks ?? [])].reverse().map((w) => (
            <option key={w} value={w}>{weekLabel(w)}</option>
          ))}
        </select>
        {data && (
          <span className="text-xs text-slate-500">
            {data.season} · {weekLabel(data.week)} · {data.sims.toLocaleString()} simulations
          </span>
        )}
      </div>

      {q.isError && (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 px-4 py-3 text-sm text-slate-400">
          Playoff odds aren&apos;t available yet.
        </div>
      )}
      {q.isLoading && <p className="text-sm text-slate-500">Loading…</p>}

      {data && (
        <div className="space-y-8">
          <div>
            <OddsTable teams={confTeams} />
            <p className="mt-2 text-xs text-slate-600">
              Sorted by playoff odds; the dashed line falls after the top seven. Cell shading tracks the probability.
            </p>
          </div>

          <section>
            <h2 className="mb-3 text-sm font-semibold text-slate-200">Playoff odds by week</h2>
            <div className="grid gap-4 md:grid-cols-2">
              {DIVISIONS.map((d) => (
                <DivisionChart
                  key={d}
                  title={`${conference} ${d}`}
                  teams={confTeams.filter((t) => t.division === d)}
                  weeks={shownWeeks}
                />
              ))}
            </div>
          </section>

          <Calibration />

          <p className="text-xs leading-relaxed text-slate-600">
            How it works: each remaining game is decided by the Elo win probability, with every team&apos;s rating jittered in
            each simulated season because no rating is exact (how much jitter was tuned on 2010–2019 results). Seeding uses
            the main NFL tiebreakers — head-to-head, division record, conference record, strength of victory — then a coin
            flip; the full rulebook has a few more steps. The model doesn&apos;t know about injuries.
          </p>
        </div>
      )}
    </div>
  );
}
