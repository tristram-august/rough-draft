"use client";

import * as React from "react";
import { useQueries } from "@tanstack/react-query";
import { FantasyBoard } from "./fantasy-board";
import { Segmented } from "./segmented";
import {
  SCORING_LABELS,
  fetchFantasyPlayer,
  type FantasyBoardRow,
  type Scoring,
} from "../lib/fantasy";

const POSITION_COLORS: Record<string, string> = {
  QB: "text-rose-400",
  RB: "text-emerald-400",
  WR: "text-sky-400",
  TE: "text-amber-400",
  K: "text-slate-400",
  DST: "text-violet-400",
};

type SelectedPlayer = { gsisId: string; name: string; position: string; team: string | null };

export function CompareTool({
  season,
  scoring,
  onScoringChange,
}: {
  season: number;
  scoring: Scoring;
  onScoringChange: (scoring: Scoring) => void;
}) {
  const [selected, setSelected] = React.useState<SelectedPlayer[]>([]);

  const toggle = React.useCallback((id: string, row: FantasyBoardRow) => {
    setSelected((prev) => {
      if (prev.some((p) => p.gsisId === id)) return prev.filter((p) => p.gsisId !== id);
      if (prev.length >= 4) return prev;
      return [...prev, { gsisId: id, name: row.player_name, position: row.position, team: row.team }];
    });
  }, []);

  const selectedIds = React.useMemo(() => new Set(selected.map((p) => p.gsisId)), [selected]);

  // Our own game-log data, not FantasyPros -- no rate limit or external
  // outage to work around, so this just reacts live as picks change instead
  // of needing an explicit "Compare" submit step.
  const playerQueries = useQueries({
    queries: selected.map((p) => ({
      queryKey: ["fantasy-player", p.gsisId, scoring, season],
      queryFn: () => fetchFantasyPlayer(p.gsisId, scoring, season),
      enabled: selected.length >= 2,
    })),
  });

  const anyLoading = playerQueries.some((q) => q.isLoading);
  const anyError = playerQueries.some((q) => q.isError);
  const allLoaded = selected.length >= 2 && playerQueries.every((q) => q.data);

  // Same-page weeks x players grid. REG season only -- playoff/preseason
  // weeks would otherwise mix into the same week numbers.
  const weeks = React.useMemo(() => {
    const set = new Set<number>();
    for (const q of playerQueries) {
      for (const g of q.data?.games ?? []) {
        if (g.season_type === "REG" && g.week != null) set.add(g.week);
      }
    }
    return [...set].sort((a, b) => a - b);
  }, [playerQueries]);

  const pointsByPlayerWeek = React.useMemo(() => {
    const map = new Map<string, Map<number, number>>();
    selected.forEach((p, i) => {
      const byWeek = new Map<number, number>();
      for (const g of playerQueries[i]?.data?.games ?? []) {
        if (g.season_type === "REG" && g.week != null) byWeek.set(g.week, g.fantasy_points);
      }
      map.set(p.gsisId, byWeek);
    });
    return map;
  }, [selected, playerQueries]);

  // Scroll the grid into view the moment there's something to show --
  // results used to render below the full ~500-row board with no visual
  // cue, which reliably looked like picking players did nothing.
  const resultsRef = React.useRef<HTMLDivElement>(null);
  const prevShownRef = React.useRef(false);
  React.useEffect(() => {
    const shown = selected.length >= 2;
    if (shown && !prevShownRef.current) {
      resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    prevShownRef.current = shown;
  }, [selected.length]);

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-slate-800 bg-slate-900/30 px-4 py-3 text-sm text-slate-400">
        Check 2–4 players below to compare their fantasy points, week by week.
      </div>

      <Segmented
        ariaLabel="Scoring format"
        value={scoring}
        onChange={onScoringChange}
        options={(["ppr", "half", "std"] as const).map((k) => ({ value: k, label: SCORING_LABELS[k] }))}
      />

      <div className="sticky top-20 z-10 flex items-center gap-3 rounded-2xl border border-slate-700 bg-slate-950/95 px-4 py-3 shadow-lg backdrop-blur">
        <span className="text-sm text-slate-300">Comparing ({selected.length}/4)</span>
        {selected.length > 0 && (
          <button
            type="button"
            onClick={() => setSelected([])}
            className="rounded-xl border border-slate-700 px-2.5 py-1 text-xs text-slate-400 transition-colors hover:text-slate-200"
          >
            Clear
          </button>
        )}
        {selected.length === 1 && (
          <span className="text-xs text-slate-600">Pick at least one more player.</span>
        )}
        {anyLoading && <span className="text-xs text-slate-500">Loading…</span>}
        {anyError && (
          <span className="text-xs text-red-400">Couldn&apos;t load one or more players.</span>
        )}
      </div>

      {allLoaded && (
        <div ref={resultsRef} className="overflow-x-auto rounded-3xl border border-slate-800 scroll-mt-20">
          <table className="w-full border-collapse text-sm">
            <thead className="bg-slate-900/60">
              <tr className="text-xs uppercase tracking-wide text-slate-500">
                <th className="px-3 py-2.5 text-left font-semibold">Week</th>
                {selected.map((p) => (
                  <th key={p.gsisId} className="px-3 py-2.5 text-right font-semibold">
                    <span className={POSITION_COLORS[p.position] ?? "text-slate-400"}>{p.position}</span>{" "}
                    {p.name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {weeks.map((w) => (
                <tr key={w} className="border-t border-slate-800/60">
                  <td className="px-3 py-2 text-xs text-slate-500">Wk {w}</td>
                  {selected.map((p) => {
                    const pts = pointsByPlayerWeek.get(p.gsisId)?.get(w);
                    return (
                      <td key={p.gsisId} className="px-3 py-2 text-right tabular-nums">
                        {pts != null ? (
                          <span className="text-slate-100">{pts.toFixed(1)}</span>
                        ) : (
                          <span className="text-slate-700">—</span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
              <tr className="border-t border-slate-700 bg-slate-900/40 font-semibold">
                <td className="px-3 py-2 text-xs text-slate-400">Total</td>
                {selected.map((p) => {
                  const byWeek = pointsByPlayerWeek.get(p.gsisId);
                  const total = [...(byWeek?.values() ?? [])].reduce((a, b) => a + b, 0);
                  const games = byWeek?.size ?? 0;
                  return (
                    <td key={p.gsisId} className="px-3 py-2 text-right tabular-nums">
                      <div className="text-slate-100">{total.toFixed(1)}</div>
                      <div className="text-[11px] font-normal text-slate-500">
                        {games > 0 ? `${(total / games).toFixed(1)}/gm` : "—"}
                      </div>
                    </td>
                  );
                })}
              </tr>
            </tbody>
          </table>
          {weeks.length === 0 && (
            <p className="px-3 py-3 text-sm text-slate-500">
              No {season} regular-season games logged yet for these players.
            </p>
          )}
          <p className="px-3 py-2 text-xs leading-relaxed text-slate-600">
            Fantasy points from actual game-by-game production, not projections.
          </p>
        </div>
      )}

      <FantasyBoard
        season={season}
        selectable
        selectedIds={selectedIds}
        onToggleSelect={toggle}
        maxSelected={4}
      />
    </div>
  );
}
