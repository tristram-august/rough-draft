"use client";

import * as React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "./page-header";
import { fetchScorecard, type ScoreCall, type ScoreLine, type Scorecard } from "../lib/betting";

const SEASON = 2026;
const MODEL = "#3987e5";

const pct = (v: number | null, digits = 1) => (v == null ? "—" : `${(v * 100).toFixed(digits)}%`);

function Tile({ label, value, sub }: { label: string; value: string; sub: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
      <div className="text-[11px] font-medium uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1.5 text-2xl font-semibold tabular-nums text-slate-100">{value}</div>
      <div className="mt-1 text-xs leading-snug text-slate-400">{sub}</div>
    </div>
  );
}

function verdict(o: ScoreLine) {
  if (o.model_hit_rate == null || o.under_hit_rate == null) return null;
  const edge = (o.model_hit_rate - o.under_hit_rate) * 100;
  if (edge > 1) return `The model is beating the "take every under" baseline by ${edge.toFixed(1)} points so far.`;
  if (edge < -1) return `So far the model is ${Math.abs(edge).toFixed(1)} points behind simply taking every under — treat its picks with caution.`;
  return `So far the model is roughly tied with simply taking every under (${edge >= 0 ? "+" : ""}${edge.toFixed(1)} points) — it hasn't shown a real edge against these lines yet.`;
}

function WeeklyChart({ weeks }: { weeks: Scorecard["weeks"] }) {
  const graded = weeks.filter((w) => w.n > 0);
  const boxRef = React.useRef<HTMLDivElement>(null);
  const [width, setWidth] = React.useState(720);
  const [hover, setHover] = React.useState<number | null>(null);
  React.useEffect(() => {
    const el = boxRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => setWidth(Math.max(280, Math.round(e.contentRect.width))));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  if (!graded.length) return null;

  const H = 220;
  const padL = 40;
  const padB = 34;
  const padT = 16;
  const edges = graded.map((w) => ((w.model_hit_rate ?? 0) - (w.under_hit_rate ?? 0)) * 100);
  const maxAbs = Math.max(5, Math.ceil(Math.max(...edges.map(Math.abs))));
  const y = (v: number) => padT + ((maxAbs - v) / (2 * maxAbs)) * (H - padT - padB);
  const zeroY = y(0);
  const band = (width - padL) / graded.length;
  const barW = Math.min(46, band * 0.5);
  const active = hover != null ? graded[hover] : null;

  return (
    <section className="rounded-3xl border border-slate-800 bg-slate-900/30 p-5">
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-200">Edge over &ldquo;take every under,&rdquo; by week</h2>
          <p className="text-[11px] text-slate-500">Model hit rate minus the every-under hit rate, in percentage points. Above the line = the model helped.</p>
        </div>
        <span className="flex items-center gap-1.5 text-[11px] text-slate-400">
          <span className="h-2.5 w-3 rounded-sm opacity-45" style={{ background: MODEL }} />Rebuilt week
        </span>
      </div>
      <div className="relative" ref={boxRef}>
        <svg width={width} height={H} viewBox={`0 0 ${width} ${H}`} className="block max-w-full" role="img" aria-label="Weekly edge over the every-under baseline">
          {[-maxAbs, 0, maxAbs].map((v) => (
            <g key={v}>
              <line x1={padL} x2={width} y1={y(v)} y2={y(v)} stroke={v === 0 ? "#475569" : "#1e293b"} />
              <text x={padL - 6} y={y(v) + 3.5} textAnchor="end" fontSize={10} fill="#64748b">{v > 0 ? `+${v}` : v}</text>
            </g>
          ))}
          {graded.map((w, i) => {
            const cx = padL + band * i + band / 2;
            const e = edges[i];
            const top = Math.min(y(e), zeroY);
            const h = Math.max(2, Math.abs(y(e) - zeroY));
            return (
              <g key={w.week}>
                <rect x={cx - barW / 2} y={top} width={barW} height={h} rx={4} fill={e >= 0 ? MODEL : "#e66767"} opacity={w.source === "snapshot" ? 1 : 0.45} />
                <text x={cx} y={e >= 0 ? top - 4 : top + h + 12} textAnchor="middle" fontSize={11} fill="#cbd5e1">
                  {e > 0 ? "+" : ""}{e.toFixed(1)}
                </text>
                <text x={cx} y={H - 18} textAnchor="middle" fontSize={11} fill="#94a3b8">W{w.week}</text>
                <text x={cx} y={H - 5} textAnchor="middle" fontSize={10} fill="#64748b">{w.source === "snapshot" ? "live" : "rebuilt"}</text>
                <rect x={padL + band * i} y={0} width={band} height={H} fill="transparent" onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)} />
              </g>
            );
          })}
        </svg>
        {active && hover != null && (
          <div
            className="pointer-events-none absolute top-0 z-10 w-52 rounded-xl border border-slate-700 bg-slate-950/95 px-3 py-2 text-xs shadow-lg"
            style={(hover + 0.5) / graded.length <= 0.5 ? { left: `calc(${((padL + band * (hover + 0.5)) / width) * 100}% + 30px)` } : { right: `calc(${100 - ((padL + band * (hover + 0.5)) / width) * 100}% + 30px)` }}
          >
            <div className="mb-1 font-semibold text-slate-100">Week {active.week} · {active.source === "snapshot" ? "saved before kickoff" : "rebuilt afterwards"}</div>
            <div className="grid grid-cols-2 gap-x-2 tabular-nums text-slate-300">
              <span className="text-slate-500">Model</span><span className="text-right">{pct(active.model_hit_rate)} ({active.model_hits}/{active.n})</span>
              <span className="text-slate-500">Every under</span><span className="text-right">{pct(active.under_hit_rate)}</span>
              <span className="text-slate-500">Confident</span><span className="text-right">{active.confident_hits}/{active.confident_n}</span>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

function ScoreTable({ title, rows, first }: { title: string; rows: (ScoreLine & { key: string; name: React.ReactNode; extra?: React.ReactNode })[]; first: string }) {
  return (
    <section className="overflow-x-auto rounded-3xl border border-slate-800">
      <div className="border-b border-slate-800 bg-slate-900/40 px-4 py-2.5 text-sm font-semibold text-slate-200">{title}</div>
      <table className="w-full border-collapse text-sm sm:min-w-[640px]">
        <thead>
          <tr className="text-[11px] uppercase tracking-wide text-slate-500">
            <th className="px-4 py-2 text-left font-semibold">{first}</th>
            <th className="px-3 py-2 text-right font-semibold">Graded</th>
            <th className="px-3 py-2 text-right font-semibold">Model hit</th>
            <th className="px-3 py-2 text-right font-semibold">Every under</th>
            <th className="px-3 py-2 text-right font-semibold">Edge</th>
            <th className="px-3 py-2 text-right font-semibold">Confident</th>
            <th className="px-4 py-2 text-right font-semibold" title="Lower is better; always saying 50% scores 0.250">Brier</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const edge = r.model_hit_rate != null && r.under_hit_rate != null ? (r.model_hit_rate - r.under_hit_rate) * 100 : null;
            return (
              <tr key={r.key} className="border-t border-slate-800/60">
                <td className="px-4 py-2 text-xs text-slate-200">{r.name}{r.extra}</td>
                <td className="px-3 py-2 text-right text-xs tabular-nums text-slate-400">{r.n || "—"}</td>
                <td className="px-3 py-2 text-right text-xs font-semibold tabular-nums text-slate-100">{pct(r.model_hit_rate)}</td>
                <td className="px-3 py-2 text-right text-xs tabular-nums text-slate-400">{pct(r.under_hit_rate)}</td>
                <td className={`px-3 py-2 text-right text-xs tabular-nums ${edge == null ? "text-slate-600" : edge > 1 ? "text-sky-300" : edge < -1 ? "text-rose-300" : "text-slate-400"}`}>
                  {edge == null ? "—" : `${edge > 0 ? "+" : ""}${edge.toFixed(1)}`}
                </td>
                <td className="px-3 py-2 text-right text-xs tabular-nums text-slate-300">{r.confident_n ? `${r.confident_hits}/${r.confident_n}` : "—"}</td>
                <td className="px-4 py-2 text-right text-xs tabular-nums text-slate-400">{r.brier?.toFixed(3) ?? "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}

function Calls({ title, calls }: { title: string; calls: ScoreCall[] }) {
  return (
    <section className="rounded-3xl border border-slate-800 bg-slate-900/30 p-5">
      <h2 className="mb-3 text-sm font-semibold text-slate-200">{title}</h2>
      <ul className="space-y-2">
        {calls.map((c) => (
          <li key={`${c.week}-${c.name}-${c.stat}`} className="flex items-baseline justify-between gap-3 text-xs">
            <div className="min-w-0">
              <span className="font-medium text-slate-100">{c.name}</span>
              <span className="ml-1.5 text-slate-500">W{c.week} {c.team} vs {c.opponent}</span>
              <div className="text-slate-400">
                {c.side === "over" ? "Over" : "Under"} {c.line} {c.label} · went {c.actual % 1 ? c.actual.toFixed(1) : c.actual}
              </div>
            </div>
            <span className="shrink-0 tabular-nums text-slate-300">{pct(c.confidence, 0)}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function PropScorecardPage() {
  const q = useQuery({ queryKey: ["prop-scorecard", SEASON], queryFn: () => fetchScorecard(SEASON) });
  const d = q.data;
  const pending = d?.weeks.reduce((s, w) => s + w.pending, 0) ?? 0;
  const pendingWeeks = d?.weeks.filter((w) => w.pending > 0).map((w) => w.week) ?? [];

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <Link href="/betting" className="text-xs text-slate-500 transition-colors hover:text-slate-300">← Prop board</Link>
      <div className="mt-3">
        <PageHeader
          eyebrow="Player Props"
          title="Model Scorecard"
          subtitle="Every week the prop board is saved before kickoff and graded after the games. A pick is the side the model leans — over if it gives the over 50% or more. Players who didn't play are voided, not counted as misses."
        />
      </div>

      {q.isError && <div className="rounded-2xl border border-slate-800 bg-slate-900/40 px-4 py-3 text-sm text-slate-400">No graded picks yet.</div>}
      {q.isLoading && <p className="text-sm text-slate-500">Loading…</p>}

      {d && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Tile label="Model hit rate" value={pct(d.overall.model_hit_rate)} sub={`${d.overall.model_hits.toLocaleString()} of ${d.overall.n.toLocaleString()} graded picks`} />
            <Tile label="Take every under" value={pct(d.overall.under_hit_rate)} sub="The no-model baseline — unders hit often against projection-based lines" />
            <Tile
              label={`Confident picks (${Math.round(d.confident_threshold * 100)}%+)`}
              value={d.overall.confident_n ? pct(d.overall.confident_hits / d.overall.confident_n) : "—"}
              sub={`${d.overall.confident_hits} of ${d.overall.confident_n}`}
            />
            <Tile label="Brier score" value={d.overall.brier?.toFixed(3) ?? "—"} sub="Lower is better · always saying 50% scores 0.250" />
          </div>

          {verdict(d.overall) && (
            <div className="rounded-2xl border border-slate-700 bg-slate-900/60 px-4 py-3 text-sm text-slate-200">
              {verdict(d.overall)}
              {pending > 0 && (
                <span className="text-slate-400"> {pending} picks from week {pendingWeeks.join(", ")} are waiting on games.</span>
              )}
            </div>
          )}

          <WeeklyChart weeks={d.weeks} />

          <ScoreTable
            title="By week"
            first="Week"
            rows={d.weeks.map((w) => ({
              ...w,
              key: String(w.week),
              name: `Week ${w.week}`,
              extra: (
                <span className="ml-2 text-[11px] text-slate-500">
                  {w.source === "snapshot" ? "saved before kickoff" : w.source === "reconstructed" ? "rebuilt" : "mixed"}
                  {w.pending ? ` · ${w.pending} pending` : ""}
                  {w.voids ? ` · ${w.voids} void` : ""}
                </span>
              ),
            }))}
          />

          <ScoreTable title="By stat" first="Stat" rows={d.by_stat.map((s) => ({ ...s, key: s.stat, name: s.label }))} />

          <section className="rounded-3xl border border-slate-800 bg-slate-900/30 p-5">
            <h2 className="text-sm font-semibold text-slate-200">Do the percentages mean what they say?</h2>
            <p className="mt-1 max-w-2xl text-xs leading-relaxed text-slate-500">
              If the model is honest, props it gave a 30% chance of going over should go over about 30% of the time. Big gaps
              mean the percentages are overconfident or underconfident.
            </p>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full max-w-xl border-collapse text-sm">
                <thead>
                  <tr className="text-[11px] uppercase tracking-wide text-slate-500">
                    <th className="py-2 pr-3 text-left font-semibold">Model said over</th>
                    <th className="px-3 py-2 text-right font-semibold">Average</th>
                    <th className="px-3 py-2 text-right font-semibold">Actually went over</th>
                    <th className="px-3 py-2 text-right font-semibold">Props</th>
                  </tr>
                </thead>
                <tbody>
                  {d.calibration.map((b) => (
                    <tr key={b.lo} className="border-t border-slate-800/60">
                      <td className="py-1.5 pr-3 text-xs text-slate-400">{Math.round(b.lo * 100)}–{Math.round(b.hi * 100)}%</td>
                      <td className="px-3 py-1.5 text-right text-xs tabular-nums text-slate-300">{pct(b.predicted)}</td>
                      <td className="px-3 py-1.5 text-right text-xs font-semibold tabular-nums text-slate-100">{pct(b.over_rate)}</td>
                      <td className="px-3 py-1.5 text-right text-xs tabular-nums text-slate-500">{b.n.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <div className="grid gap-4 lg:grid-cols-2">
            <Calls title="Most confident hits" calls={d.best_calls} />
            <Calls title="Most confident misses" calls={d.worst_calls} />
          </div>

          <p className="text-xs leading-relaxed text-slate-600">
            &ldquo;Rebuilt&rdquo; weeks were recreated after the fact from data available before that week — the results
            couldn&apos;t leak in, but they use today&apos;s version of the model and it didn&apos;t know about late scratches.
            The true track record is the weeks saved before kickoff. Lines are FantasyPros-based, not sportsbook lines.
          </p>
        </div>
      )}
    </div>
  );
}
