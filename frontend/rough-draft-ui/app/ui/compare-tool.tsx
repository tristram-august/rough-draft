"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { FantasyBoard } from "./fantasy-board";
import { fetchCompare } from "../lib/compare";

const SCORING_LABELS: Record<string, string> = { STD: "Standard", PPR: "PPR", HALF: "Half PPR" };

function avgRank(ranks: { rank: string }[] | undefined): number | null {
  if (!ranks || ranks.length === 0) return null;
  const nums = ranks.map((r) => parseFloat(r.rank)).filter((n) => !Number.isNaN(n));
  if (nums.length === 0) return null;
  return nums.reduce((a, b) => a + b, 0) / nums.length;
}

export function CompareTool({ season }: { season: number }) {
  const [selected, setSelected] = React.useState<Set<number>>(new Set());

  const toggle = React.useCallback((id: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const ids = React.useMemo(() => [...selected].sort((a, b) => a - b), [selected]);

  const compareQuery = useQuery({
    queryKey: ["compare", ids],
    queryFn: () => fetchCompare(ids),
    enabled: false,
  });

  const canCompare = ids.length >= 2 && ids.length <= 4;

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-slate-800 bg-slate-900/30 px-4 py-3 text-sm text-slate-400">
        Check 2–4 players on the board below, then compare how individual experts rank each of
        them.
      </div>

      <FantasyBoard season={season} selectable selectedIds={selected} onToggleSelect={toggle} maxSelected={4} />

      <div className="sticky bottom-4 flex items-center gap-3 rounded-2xl border border-slate-700 bg-slate-950/95 px-4 py-3 shadow-lg backdrop-blur">
        <span className="text-sm text-slate-300">
          Compare Selected ({ids.length}/4)
        </span>
        <button
          type="button"
          disabled={!canCompare}
          onClick={() => compareQuery.refetch()}
          className="rounded-xl border border-sky-700 bg-sky-950/40 px-3 py-1.5 text-xs font-medium text-sky-300 transition-colors hover:bg-sky-900/40 disabled:cursor-not-allowed disabled:opacity-30"
        >
          {compareQuery.isFetching ? "Comparing…" : "Compare"}
        </button>
        {compareQuery.isError && (
          <span className="text-xs text-red-400">Couldn&apos;t load the comparison.</span>
        )}
      </div>

      {compareQuery.data && (
        <div className="overflow-x-auto rounded-3xl border border-slate-800">
          <table className="w-full border-collapse text-sm">
            <thead className="bg-slate-900/60">
              <tr className="text-xs uppercase tracking-wide text-slate-500">
                <th className="px-3 py-2.5 text-left font-semibold">Player</th>
                {Object.keys(compareQuery.data.rankings).map((scoring) => (
                  <th key={scoring} className="px-3 py-2.5 text-right font-semibold">
                    {SCORING_LABELS[scoring] ?? scoring}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {Object.entries(compareQuery.data.players).map(([playerId, info]) => (
                <tr key={playerId} className="border-t border-slate-800/60">
                  <td className="px-3 py-2">
                    <div className="font-medium text-slate-100">{info.player_name}</div>
                    <div className="text-xs text-slate-500">
                      {info.player_position_id} · {info.player_team_id}
                    </div>
                  </td>
                  {Object.keys(compareQuery.data!.rankings).map((scoring) => {
                    const avg = avgRank(compareQuery.data!.rankings[scoring]?.[playerId]);
                    const count = compareQuery.data!.rankings[scoring]?.[playerId]?.length ?? 0;
                    return (
                      <td key={scoring} className="px-3 py-2 text-right tabular-nums">
                        {avg != null ? (
                          <>
                            <span className="text-slate-100">{avg.toFixed(1)}</span>
                            <span className="ml-1 text-xs text-slate-600">({count} experts)</span>
                          </>
                        ) : (
                          <span className="text-slate-700">—</span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
          <p className="px-3 py-2 text-xs leading-relaxed text-slate-600">
            Average expert rank per scoring format, live from FantasyPros — lower is better.
          </p>
        </div>
      )}
    </div>
  );
}
