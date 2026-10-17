"use client";

import * as React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "./page-header";
import { Segmented } from "./segmented";
import { teamColor } from "../lib/team-colors";
import {
  fetchBoardProb,
  fetchPropBoard,
  overThreshold,
  type BoardRow,
  type StatKey,
} from "../lib/betting";

const SEASON = 2026;
const PAGE = 100;

type Side = "over" | "under";
type SortKey = "model" | "line" | "l5" | "l10" | "szn" | "h2h" | "matchup" | "player";
type Override = { line: number; p_over: number | null; error?: boolean };

const selectClass =
  "rounded-xl border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs font-medium text-slate-300 outline-none transition-colors focus:border-slate-600";

const rowKey = (r: BoardRow) => `${r.gsis_id}:${r.stat}`;
const ALIGN = { left: "text-left", center: "text-center", right: "text-right" } as const;

// Diverging around 50%: blue leans toward the pick hitting, red away. Validated pair for dark mode.
function leanStyle(p: number | null): React.CSSProperties {
  if (p == null) return {};
  const strength = Math.min(0.55, Math.abs(p - 0.5) * 1.3);
  const rgb = p >= 0.5 ? "57, 135, 229" : "230, 103, 103";
  return { background: `rgba(${rgb}, ${strength.toFixed(3)})` };
}

function hitRate(values: number[], line: number, side: Side): number | null {
  if (!values.length) return null;
  const hits = values.filter((v) => (side === "over" ? v > line : v < line)).length;
  return hits / values.length;
}

function streak(values: number[], line: number, side: Side): number {
  let n = 0;
  for (const v of values) {
    if (side === "over" ? v > line : v < line) n++;
    else break;
  }
  return n;
}

function ordinal(n: number) {
  const m = n % 100;
  if (m >= 11 && m <= 13) return `${n}th`;
  return `${n}${({ 1: "st", 2: "nd", 3: "rd" } as Record<number, string>)[n % 10] ?? "th"}`;
}

function fmtLine(v: number) {
  return Number.isInteger(v) ? v.toFixed(0) : v.toFixed(1);
}

type Derived = {
  row: BoardRow;
  key: string;
  line: number;
  overridden: boolean;
  pending: boolean;
  p: number | null;
  l5: number | null;
  l10: number | null;
  szn: number | null;
  h2h: number | null;
  streak: number;
};

function RateCell({ rate, n }: { rate: number | null; n: number }) {
  return (
    <td className="px-1 py-1">
      <div
        className="rounded-md px-1.5 py-1.5 text-center text-xs tabular-nums text-slate-200"
        style={leanStyle(rate)}
        title={rate == null ? "No games" : `${Math.round(rate * n)} of ${n} games`}
      >
        {rate == null ? "—" : `${Math.round(rate * 100)}%`}
      </div>
    </td>
  );
}

function LineInput({
  value,
  original,
  onCommit,
  onReset,
}: {
  value: number;
  original: number;
  onCommit: (v: number) => void;
  onReset: () => void;
}) {
  const [draft, setDraft] = React.useState(fmtLine(value));
  React.useEffect(() => setDraft(fmtLine(value)), [value]);
  const commit = () => {
    const v = Number(draft);
    if (!Number.isFinite(v) || v < 0 || v > 999) {
      setDraft(fmtLine(value));
      return;
    }
    const rounded = Math.round(v * 2) / 2;
    if (rounded !== value) onCommit(rounded);
    else setDraft(fmtLine(value));
  };
  return (
    <div className="flex items-center justify-end gap-1">
      <input
        aria-label="Line"
        inputMode="decimal"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === "Enter") (e.target as HTMLInputElement).blur();
          if (e.key === "Escape") setDraft(fmtLine(value));
        }}
        className={`w-16 rounded-md border bg-slate-950/60 px-1.5 py-1 text-right text-xs tabular-nums outline-none transition-colors focus:border-slate-500 ${
          value !== original ? "border-amber-500/60 text-amber-200" : "border-slate-800 text-slate-100"
        }`}
      />
      {value !== original && (
        <button type="button" onClick={onReset} title={`Reset to ${fmtLine(original)}`} className="text-[11px] text-slate-500 hover:text-slate-300">
          ↺
        </button>
      )}
    </div>
  );
}

function SortTh({
  label,
  k,
  sort,
  onSort,
  title,
  align = "center",
}: {
  label: string;
  k: SortKey;
  sort: { key: SortKey; desc: boolean };
  onSort: (k: SortKey) => void;
  title?: string;
  align?: "left" | "center" | "right";
}) {
  const active = sort.key === k;
  return (
    <th scope="col" className={`px-2 py-2.5 font-semibold ${ALIGN[align]}`} aria-sort={active ? (sort.desc ? "descending" : "ascending") : "none"} title={title}>
      <button type="button" onClick={() => onSort(k)} className="inline-flex items-center gap-1 uppercase tracking-wide transition-colors hover:text-slate-200">
        {label}
        <span className={`text-[9px] ${active ? "text-slate-300" : "text-slate-700"}`}>{active ? (sort.desc ? "▼" : "▲") : "▾"}</span>
      </button>
    </th>
  );
}

export function PropBoardPage() {
  const [side, setSide] = React.useState<Side>("over");
  const [position, setPosition] = React.useState("ALL");
  const [stat, setStat] = React.useState<StatKey | "ALL">("ALL");
  const [game, setGame] = React.useState("ALL");
  const [search, setSearch] = React.useState("");
  const [sort, setSort] = React.useState<{ key: SortKey; desc: boolean }>({ key: "model", desc: true });
  const [limit, setLimit] = React.useState(PAGE);
  const [overrides, setOverrides] = React.useState<Record<string, Override>>({});

  const q = useQuery({ queryKey: ["prop-board", SEASON], queryFn: () => fetchPropBoard(SEASON), staleTime: 5 * 60 * 1000 });
  const board = q.data;
  const statLabel = React.useMemo(
    () => Object.fromEntries((board?.stats ?? []).map((s) => [s.key, s.label])) as Record<string, string>,
    [board],
  );

  const games = React.useMemo(() => {
    const seen = new Map<string, string>();
    for (const r of board?.rows ?? []) {
      const away = r.home ? r.opponent : r.team;
      const home = r.home ? r.team : r.opponent;
      seen.set(`${away}@${home}`, `${away} @ ${home}`);
    }
    return [...seen.entries()].sort((a, b) => a[1].localeCompare(b[1]));
  }, [board]);

  async function commitLine(r: BoardRow, line: number) {
    const key = rowKey(r);
    if (line === r.line) {
      setOverrides((o) => {
        const next = { ...o };
        delete next[key];
        return next;
      });
      return;
    }
    setOverrides((o) => ({ ...o, [key]: { line, p_over: null } }));
    try {
      const res = await fetchBoardProb({ season: board!.season, week: board!.week, stat: r.stat, gsisId: r.gsis_id, opponent: r.opponent, line });
      setOverrides((o) => (o[key]?.line === line ? { ...o, [key]: { line, p_over: res.p_over } } : o));
    } catch {
      setOverrides((o) => (o[key]?.line === line ? { ...o, [key]: { line, p_over: null, error: true } } : o));
    }
  }

  const derived: Derived[] = React.useMemo(() => {
    const needle = search.trim().toLowerCase();
    return (board?.rows ?? [])
      .filter((r) => position === "ALL" || r.position === position)
      .filter((r) => stat === "ALL" || r.stat === stat)
      .filter((r) => {
        if (game === "ALL") return true;
        const away = r.home ? r.opponent : r.team;
        const home = r.home ? r.team : r.opponent;
        return `${away}@${home}` === game;
      })
      .filter((r) => !needle || r.name.toLowerCase().includes(needle) || r.team.toLowerCase() === needle)
      .map((r) => {
        const key = rowKey(r);
        const o = overrides[key];
        const line = o?.line ?? r.line;
        const pOver = o ? o.p_over : r.p_over;
        const recent = r.recent.map((g) => g.value);
        return {
          row: r,
          key,
          line,
          overridden: o != null,
          pending: o != null && o.p_over == null && !o.error,
          p: pOver == null ? null : side === "over" ? pOver : 1 - pOver,
          l5: hitRate(recent.slice(0, 5), line, side),
          l10: hitRate(recent, line, side),
          szn: hitRate(r.season_values, line, side),
          h2h: hitRate(r.h2h.map((g) => g.value), line, side),
          streak: streak(recent, line, side),
        };
      });
  }, [board, position, stat, game, search, overrides, side]);

  const sorted = React.useMemo(() => {
    const val = (d: Derived): number | string | null => {
      switch (sort.key) {
        case "model": return d.p;
        case "line": return d.line;
        case "l5": return d.l5;
        case "l10": return d.l10;
        case "szn": return d.szn;
        case "h2h": return d.h2h;
        case "matchup": return d.row.matchup_rank == null ? null : side === "over" ? -d.row.matchup_rank : d.row.matchup_rank;
        case "player": return d.row.name;
      }
    };
    return [...derived].sort((a, b) => {
      const va = val(a);
      const vb = val(b);
      if (va == null && vb == null) return 0;
      if (va == null) return 1;
      if (vb == null) return -1;
      const cmp = typeof va === "string" ? va.localeCompare(vb as string) : (va as number) - (vb as number);
      return sort.desc ? -cmp : cmp;
    });
  }, [derived, sort, side]);

  function onSort(k: SortKey) {
    setSort((s) => (s.key === k ? { key: k, desc: !s.desc } : { key: k, desc: k !== "player" }));
  }

  React.useEffect(() => setLimit(PAGE), [position, stat, game, search, side]);

  const shown = sorted.slice(0, limit);
  const statsForPosition = (board?.stats ?? []).filter((s) => position === "ALL" || s.positions.includes(position));

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <PageHeader
        eyebrow="Player Props"
        title="Prop Board"
        subtitle="Every player and stat for the week, with our model's odds of clearing the line, recent hit rates and the matchup. Lines start at the FantasyPros projection — type any line, like the one in your app, to re-run the odds."
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Segmented
          ariaLabel="Over or under"
          value={side}
          onChange={(v) => setSide(v as Side)}
          options={[{ value: "over", label: "Overs" }, { value: "under", label: "Unders" }]}
        />
        <Segmented
          ariaLabel="Position"
          value={position}
          onChange={(v) => {
            setPosition(v);
            setStat("ALL");
          }}
          options={["ALL", "QB", "RB", "WR", "TE"].map((p) => ({ value: p, label: p === "ALL" ? "All" : p }))}
        />
        <select aria-label="Stat" value={stat} onChange={(e) => setStat(e.target.value as StatKey | "ALL")} className={selectClass}>
          <option value="ALL">All stats</option>
          {statsForPosition.map((s) => (
            <option key={s.key} value={s.key}>{s.label}</option>
          ))}
        </select>
        <select aria-label="Game" value={game} onChange={(e) => setGame(e.target.value)} className={selectClass}>
          <option value="ALL">All games</option>
          {games.map(([k, label]) => (
            <option key={k} value={k}>{label}</option>
          ))}
        </select>
        <input
          aria-label="Search players"
          placeholder="Search players or team…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="min-w-[12rem] flex-1 rounded-xl border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs text-slate-200 outline-none placeholder:text-slate-600 focus:border-slate-600 sm:flex-none"
        />
        {board && (
          <span className="text-xs text-slate-500">
            {board.season} · Week {board.week} · {sorted.length.toLocaleString()} props
          </span>
        )}
        <Link href="/betting/scorecard" className="ml-auto text-xs font-medium text-sky-400 hover:text-sky-300">
          Model scorecard →
        </Link>
      </div>

      {q.isError && (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 px-4 py-3 text-sm text-slate-400">
          The prop board isn&apos;t available right now. Try again in a moment.
        </div>
      )}
      {q.isLoading && <p className="text-sm text-slate-500">Building the board…</p>}

      {board && (
        <>
          <div className="overflow-x-auto rounded-3xl border border-slate-800">
            <table className="w-full min-w-[980px] border-collapse text-sm">
              <thead className="bg-slate-900/60">
                <tr className="text-[11px] uppercase tracking-wide text-slate-500">
                  <SortTh label="Player" k="player" sort={sort} onSort={onSort} align="left" />
                  <th className="px-2 py-2.5 text-left font-semibold">Stat</th>
                  <SortTh label="Line" k="line" sort={sort} onSort={onSort} align="right" title="Defaults to the FantasyPros projection, rounded down to the half point. Edit it to re-run the model." />
                  <SortTh label={side === "over" ? "Model % over" : "Model % under"} k="model" sort={sort} onSort={onSort} />
                  <th className="px-2 py-2.5 text-right font-semibold" title="Model's average expectation for this game">Model avg</th>
                  <SortTh label="Matchup" k="matchup" sort={sort} onSort={onSort} title="Where the opponent ranks in this stat allowed per player-game this season (1st = allows the most)" />
                  <th className="px-2 py-2.5 text-center font-semibold" title="Consecutive recent games that hit">Strk</th>
                  <SortTh label="L5" k="l5" sort={sort} onSort={onSort} />
                  <SortTh label="L10" k="l10" sort={sort} onSort={onSort} />
                  <SortTh label="Szn" k="szn" sort={sort} onSort={onSort} />
                  <SortTh label="H2H" k="h2h" sort={sort} onSort={onSort} title="Games against this opponent since 2016" />
                </tr>
              </thead>
              <tbody>
                {shown.map((d) => {
                  const r = d.row;
                  const rank = r.matchup_rank;
                  const soft = rank != null && rank <= 8;
                  const tough = rank != null && rank >= 25;
                  const good = side === "over" ? soft : tough;
                  const bad = side === "over" ? tough : soft;
                  return (
                    <tr key={d.key} className="border-t border-slate-800/60 transition-colors hover:bg-slate-900/40">
                      <td className="px-3 py-1.5">
                        <div className="flex items-center gap-2">
                          <span className="h-7 w-1 shrink-0 rounded-full" style={{ background: teamColor(r.team) }} />
                          <div className="min-w-0">
                            <Link
                              href={`/betting/player?gsis_id=${r.gsis_id}&stat=${r.stat}&line=${overThreshold(d.line)}`}
                              className="block truncate font-medium text-slate-100 hover:text-white hover:underline"
                            >
                              {r.name}
                            </Link>
                            <div className="text-[11px] text-slate-500">
                              {r.position} · {r.team} {r.home ? "vs" : "@"} {r.opponent}
                              {r.thin_sample && <span className="ml-1.5 text-amber-400/80" title={`Only ${r.games_used} games of history`}>few games</span>}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-2 py-1.5 text-xs text-slate-300">{statLabel[r.stat] ?? r.stat}</td>
                      <td className="px-2 py-1.5">
                        <LineInput
                          value={d.line}
                          original={r.line}
                          onCommit={(v) => commitLine(r, v)}
                          onReset={() => commitLine(r, r.line)}
                        />
                        <div className="mt-0.5 text-right text-[10px] text-slate-600">proj {r.projection.toFixed(1)}</div>
                      </td>
                      <td className="px-1 py-1">
                        <div
                          className="rounded-md px-2 py-2 text-center text-sm font-semibold tabular-nums text-slate-50"
                          style={leanStyle(d.p)}
                        >
                          {d.pending ? "…" : d.p == null ? "—" : `${(d.p * 100).toFixed(1)}%`}
                        </div>
                      </td>
                      <td className="px-2 py-1.5 text-right text-xs tabular-nums text-slate-400">{r.mean.toFixed(1)}</td>
                      <td className="px-2 py-1.5 text-center">
                        {rank == null ? (
                          <span className="text-xs text-slate-600">—</span>
                        ) : (
                          <span
                            className={`inline-block min-w-[2.75rem] rounded-md px-1.5 py-1 text-xs tabular-nums ${
                              good ? "bg-sky-500/20 text-sky-200" : bad ? "bg-rose-500/20 text-rose-200" : "bg-slate-800/60 text-slate-300"
                            }`}
                            title={`${r.opponent} allows ${r.matchup_allowed?.toFixed(1)} per player-game (league ${r.league_allowed?.toFixed(1)})`}
                          >
                            {ordinal(rank)}
                          </span>
                        )}
                      </td>
                      <td className="px-2 py-1.5 text-center text-xs tabular-nums text-slate-300">{d.streak >= 2 ? d.streak : ""}</td>
                      <RateCell rate={d.l5} n={Math.min(5, r.recent.length)} />
                      <RateCell rate={d.l10} n={r.recent.length} />
                      <RateCell rate={d.szn} n={r.season_values.length} />
                      <RateCell rate={d.h2h} n={r.h2h.length} />
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {sorted.length > limit && (
            <div className="mt-3 flex justify-center">
              <button
                type="button"
                onClick={() => setLimit((l) => l + PAGE)}
                className="rounded-xl border border-slate-800 bg-slate-900 px-4 py-2 text-xs font-medium text-slate-300 transition-colors hover:border-slate-600"
              >
                Show more ({(sorted.length - limit).toLocaleString()} left)
              </button>
            </div>
          )}

          <p className="mt-4 text-xs leading-relaxed text-slate-600">
            Model % comes from each player&apos;s recency-weighted game log, adjusted for the opponent&apos;s defense — click a
            player for the full breakdown and the model&apos;s backtest. Over means more than the line; on a whole-number line,
            landing exactly on it is a push and counts against both sides in the hit rates. Lines are FantasyPros
            projections, not sportsbook lines. {board.disclaimer}
          </p>
        </>
      )}
    </div>
  );
}
