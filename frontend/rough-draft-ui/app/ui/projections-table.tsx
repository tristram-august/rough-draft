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

// FantasyPros' own projections cover K/DST too, unlike the computed
// Leaderboard scoring, so this filter is a superset of ../lib/fantasy's
// POSITIONS.
export const PROJECTION_POSITIONS = ["ALL", "QB", "RB", "WR", "TE", "FLEX", "K", "DST"] as const;
export type ProjectionPosition = (typeof PROJECTION_POSITIONS)[number];
export type ProjectionMode = "week" | "ros";

// mode/week/position are owned by the parent (FantasyRankingsPage) and
// mirrored into the URL there — a single writer, instead of this component
// also calling router.replace independently. Two components independently
// reading-then-writing window.location.search race each other, since
// Next's router.replace doesn't apply to window.location synchronously.
export function ProjectionsTable({
  season,
  mode,
  onModeChange,
  week,
  onWeekChange,
  position,
  onPositionChange,
}: {
  season: number;
  mode: ProjectionMode;
  onModeChange: (mode: ProjectionMode) => void;
  week: number | null;
  onWeekChange: (week: number | null) => void;
  position: ProjectionPosition;
  onPositionChange: (position: ProjectionPosition) => void;
}) {
  const weeksQuery = useQuery({
    queryKey: ["projection-weeks", season],
    queryFn: () => fetchProjectionWeeks(season),
  });
  const weeks = weeksQuery.data ?? [];
  const latestWeek = weeks[weeks.length - 1] ?? null;
  // Default to the latest week, but let the selector below override it.
  const selectedWeek = week ?? latestWeek;

  const { data, isLoading, isError } = useQuery({
    queryKey: ["projections", season, mode, selectedWeek, position],
    queryFn: () =>
      fetchProjections(
        mode === "ros"
          ? { season, ros: true, position }
          : { season, week: selectedWeek ?? 0, position }
      ),
    enabled: mode === "ros" || selectedWeek != null,
    placeholderData: (prev) => prev,
  });

  const rows = data?.rows ?? [];
  const weekAvailable = selectedWeek != null;

  // A stale week from a previously-viewed season shouldn't carry over — but
  // only reset once `season` has actually *changed* from what it was last
  // time this ran, not merely "isn't the first render." A boolean
  // didMount-style ref breaks under React 18 Strict Mode's dev-only double
  // effect invocation: the first invoke flips it true and skips (correct),
  // but the second (Strict Mode's replay of that same mount) then sees
  // `true` and misreads itself as a real subsequent change, firing the
  // reset and clobbering the week just restored from the URL. Comparing
  // against the previous *value* instead stays idempotent across however
  // many times Strict Mode replays the same mount.
  const prevSeason = React.useRef(season);
  React.useEffect(() => {
    if (prevSeason.current !== season) {
      prevSeason.current = season;
      onWeekChange(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [season]);

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
          onChange={(v) => onModeChange(v as ProjectionMode)}
          options={[
            { value: "week", label: weekAvailable ? `Week ${selectedWeek}` : "This week" },
            { value: "ros", label: "Rest of season" },
          ]}
        />
        {mode === "week" && weeks.length > 0 && (
          <select
            aria-label="Week"
            value={selectedWeek ?? ""}
            onChange={(e) => onWeekChange(e.target.value === "" ? null : Number(e.target.value))}
            className="rounded-xl border border-slate-800 bg-slate-900/40 px-3 py-1.5 text-xs font-medium text-slate-300 outline-none transition-colors focus:border-slate-600"
          >
            {weeks.map((w) => (
              <option key={w} value={w}>
                Week {w}
              </option>
            ))}
          </select>
        )}
        <Segmented
          ariaLabel="Position"
          value={position}
          onChange={onPositionChange}
          options={PROJECTION_POSITIONS.map((p) => ({ value: p, label: p === "ALL" ? "All" : p }))}
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
                <th className="px-2 py-2.5 text-left font-semibold">Opp</th>
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
                  <td className="px-2 py-2 text-xs text-slate-500">{row.opponent ?? "—"}</td>
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
