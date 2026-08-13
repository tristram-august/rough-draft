"use client";

import * as React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Segmented } from "./segmented";
import { fetchProjectionWeeks, fetchProjections } from "../lib/projections";

const POSITION_COLORS: Record<string, string> = {
  QB: "text-rose-400",
  RB: "text-emerald-400",
  WR: "text-sky-400",
  TE: "text-amber-400",
  K: "text-slate-400",
  DST: "text-violet-400",
};

export function ProjectionsTable({ season }: { season: number }) {
  const [mode, setMode] = React.useState<"week" | "ros">("week");

  const weeksQuery = useQuery({
    queryKey: ["projection-weeks", season],
    queryFn: () => fetchProjectionWeeks(season),
  });
  const latestWeek = weeksQuery.data?.[weeksQuery.data.length - 1] ?? null;

  const { data, isLoading, isError } = useQuery({
    queryKey: ["projections", season, mode, latestWeek],
    queryFn: () =>
      fetchProjections(
        mode === "ros"
          ? { season, ros: true }
          : { season, week: latestWeek ?? 0 }
      ),
    enabled: mode === "ros" || latestWeek != null,
    placeholderData: (prev) => prev,
  });

  const rows = data?.rows ?? [];
  const weekAvailable = latestWeek != null;

  if (isError) {
    return (
      <div className="rounded-2xl border border-red-900/40 bg-red-950/20 px-4 py-3 text-sm text-red-300">
        Couldn&apos;t load projections for {season}.
      </div>
    );
  }

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-center gap-2">
        <Segmented
          ariaLabel="Projection range"
          value={mode}
          onChange={(v) => setMode(v as "week" | "ros")}
          options={[
            { value: "week", label: weekAvailable ? `Week ${latestWeek}` : "This week" },
            { value: "ros", label: "Rest of season" },
          ]}
        />
        {data && (
          <span className="text-xs text-slate-600">
            {data.total} player{data.total === 1 ? "" : "s"}
          </span>
        )}
      </div>

      {isLoading && <p className="text-sm text-slate-500">Loading…</p>}

      {mode === "week" && !weekAvailable && !weeksQuery.isLoading && (
        <p className="text-sm text-slate-500">
          No weekly projections loaded for {season} yet — check Rest of season instead.
        </p>
      )}

      {data && rows.length === 0 && weekAvailable && (
        <p className="text-sm text-slate-500">No projections available.</p>
      )}

      {rows.length > 0 && (
        <div className="overflow-x-auto rounded-3xl border border-slate-800">
          <table className="w-full sm:min-w-[480px] border-collapse text-sm">
            <thead className="bg-slate-900/60">
              <tr className="text-xs uppercase tracking-wide text-slate-500">
                <th className="px-3 py-2.5 text-left font-semibold">#</th>
                <th className="px-3 py-2.5 text-left font-semibold">Player</th>
                <th className="px-2 py-2.5 text-left font-semibold">Pos</th>
                <th className="px-2 py-2.5 text-left font-semibold">Team</th>
                <th className="px-3 py-2.5 text-right font-semibold">Proj Pts</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr
                  key={`${row.gsis_id ?? row.player_name}-${i}`}
                  className="border-t border-slate-800/60 transition-colors hover:bg-slate-900/40"
                >
                  <td className="px-3 py-2 text-xs text-slate-600 tabular-nums">{i + 1}</td>
                  <td className="px-3 py-2">
                    {row.gsis_id ? (
                      <Link
                        href={`/fantasy/player/${row.gsis_id}?scoring=ppr`}
                        className="font-medium text-slate-100 transition-colors hover:text-sky-300"
                      >
                        {row.player_name}
                      </Link>
                    ) : (
                      <span className="font-medium text-slate-100">{row.player_name}</span>
                    )}
                  </td>
                  <td className="px-2 py-2">
                    <span className={`text-[11px] font-semibold ${POSITION_COLORS[row.position] ?? "text-slate-500"}`}>
                      {row.position}
                    </span>
                  </td>
                  <td className="px-2 py-2 text-xs text-slate-500">{row.team ?? "—"}</td>
                  <td className="px-3 py-2 text-right text-xs text-slate-300 tabular-nums">
                    {row.points_ppr != null ? row.points_ppr.toFixed(1) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="mt-4 text-xs leading-relaxed text-slate-600">
        PPR projected points from FantasyPros. Names link to production history where we
        could match the player.
      </p>
    </div>
  );
}
