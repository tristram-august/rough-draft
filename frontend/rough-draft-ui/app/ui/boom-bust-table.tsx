"use client";

import * as React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Segmented } from "./segmented";
import {
  POSITIONS,
  fetchFantasyWeeks,
  fetchProjectionDiff,
  type FantasyPosition,
  type ProjectionDiffRow,
  type Scoring,
  type SortDirection,
} from "../lib/fantasy";

const POSITION_COLORS: Record<string, string> = {
  QB: "text-rose-400",
  RB: "text-emerald-400",
  WR: "text-sky-400",
  TE: "text-amber-400",
};

const FLEX_POSITIONS = new Set(["RB", "WR", "TE"]);

function fmtDiff(n: number) {
  const s = n.toFixed(1);
  return n > 0 ? `+${s}` : s;
}

// week/position/direction are owned by the parent (FantasyRankingsPage) and
// mirrored into the URL there, same pattern as the Leaderboard tab -- keeps
// a single writer of the URL instead of this component also touching it.
export function BoomBustTable({
  season,
  scoring,
  week,
  onWeekChange,
  mode,
  onModeChange,
  position,
  onPositionChange,
  direction,
  onDirectionChange,
}: {
  season: number;
  scoring: Scoring;
  week: number | null;
  onWeekChange: (week: number | null) => void;
  mode: "week" | "season";
  onModeChange: (mode: "week" | "season") => void;
  position: FantasyPosition;
  onPositionChange: (position: FantasyPosition) => void;
  direction: SortDirection;
  onDirectionChange: (direction: SortDirection) => void;
}) {
  const weeksQuery = useQuery({
    queryKey: ["fantasy-weeks", season],
    queryFn: () => fetchFantasyWeeks(season),
  });
  const weeks = weeksQuery.data ?? [];
  const latestWeek = weeks[weeks.length - 1] ?? null;
  // Default to the latest played week, but let the selector override it.
  const selectedWeek = week ?? latestWeek;
  const isSeason = mode === "season";

  const diffQuery = useQuery({
    queryKey: ["projection-diff", season, isSeason ? "season" : selectedWeek, scoring],
    queryFn: () =>
      fetchProjectionDiff({ season, week: isSeason ? null : (selectedWeek as number), scoring }),
    enabled: isSeason || selectedWeek != null,
    placeholderData: (prev) => prev,
  });

  const allRows = diffQuery.data?.rows ?? [];
  const filtered =
    position === "ALL"
      ? allRows
      : position === "FLEX"
      ? allRows.filter((r) => FLEX_POSITIONS.has(r.position))
      : allRows.filter((r) => r.position === position);

  // The API already sorts by diff descending (biggest beat first); flipping
  // direction is just a reverse, no need to re-sort client-side.
  const rows = direction === "asc" ? [...filtered].reverse() : filtered;
  const maxAbs = Math.max(1, ...rows.map((r) => Math.abs(r.diff)));
  const weekAvailable = isSeason || selectedWeek != null;

  const selectClass =
    "rounded-xl border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs font-medium text-slate-300 outline-none transition-colors focus:border-slate-600";

  function toggleDirection() {
    onDirectionChange(direction === "desc" ? "asc" : "desc");
  }

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-center gap-2">
        <Segmented
          ariaLabel="Range"
          value={mode}
          onChange={onModeChange}
          options={[
            { value: "week", label: "This week" },
            { value: "season", label: "Season so far" },
          ]}
        />
        {!isSeason && (
          <select
            aria-label="Week"
            value={selectedWeek ?? ""}
            onChange={(e) => onWeekChange(e.target.value === "" ? null : Number(e.target.value))}
            className={selectClass}
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
          options={POSITIONS.map((p) => ({ value: p, label: p === "ALL" ? "All" : p }))}
        />
        <button
          type="button"
          onClick={toggleDirection}
          className="rounded-xl border border-slate-800 bg-slate-900/40 px-3 py-1.5 text-xs font-medium text-slate-300 transition-colors hover:border-slate-600"
          title={direction === "desc" ? "Showing biggest beats first" : "Showing biggest busts first"}
        >
          {direction === "desc" ? "Biggest beats first" : "Biggest busts first"}{" "}
          <span aria-hidden className="text-[10px]">
            {direction === "desc" ? "▼" : "▲"}
          </span>
        </button>
        {diffQuery.data && (
          <span className="text-xs text-slate-600">
            {rows.length} player{rows.length === 1 ? "" : "s"}
            {isSeason && diffQuery.data.weeks.length > 0 && (
              <>
                {" "}
                · weeks {diffQuery.data.weeks[0]}–{diffQuery.data.weeks[diffQuery.data.weeks.length - 1]}
              </>
            )}
          </span>
        )}
      </div>

      {diffQuery.isError && (
        <div className="rounded-2xl border border-red-900/40 bg-red-950/20 px-4 py-3 text-sm text-red-300">
          Couldn&apos;t load {isSeason ? "the season totals" : `week ${selectedWeek ?? ""}`}.
        </div>
      )}

      {!weekAvailable && !weeksQuery.isLoading && (
        <p className="text-sm text-slate-500">No played weeks for {season} yet.</p>
      )}

      {diffQuery.isLoading && <p className="text-sm text-slate-500">Loading…</p>}

      {diffQuery.data && rows.length === 0 && (
        <p className="text-sm text-slate-500">No players match those filters.</p>
      )}

      {rows.length > 0 && (
        <div
          className={`overflow-x-auto rounded-3xl border border-slate-800 transition-opacity ${
            diffQuery.isFetching ? "opacity-60" : ""
          }`}
        >
          <table className="w-full sm:min-w-[640px] border-collapse text-sm">
            <thead className="bg-slate-900/60">
              <tr className="text-xs uppercase tracking-wide text-slate-500">
                <th scope="col" className="px-3 py-2.5 text-left font-semibold">
                  #
                </th>
                <th scope="col" className="px-3 py-2.5 pl-3 text-left font-semibold">
                  Player
                </th>
                <th scope="col" className="hidden px-2 py-2.5 text-right font-semibold sm:table-cell">
                  Proj
                </th>
                <th scope="col" className="hidden px-2 py-2.5 text-right font-semibold sm:table-cell">
                  Actual
                </th>
                {isSeason && (
                  <th scope="col" className="hidden px-2 py-2.5 text-right font-semibold sm:table-cell">
                    Gm
                  </th>
                )}
                <th scope="col" className="px-3 py-2.5 pr-3 text-right font-semibold">
                  Diff
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <BoomBustRow
                  key={r.gsis_id}
                  row={r}
                  rank={i + 1}
                  season={season}
                  scoring={scoring}
                  maxAbs={maxAbs}
                  showGames={isSeason}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="mt-4 text-xs leading-relaxed text-slate-600">
        {isSeason
          ? "Projected and actual points summed across every week each player has both a projection and a box score. Positive diff = outperformed projection; negative = underperformed."
          : "Projected points from FantasyPros, actual from that week's box score. Positive diff = outperformed projection; negative = underperformed."}
      </p>
    </div>
  );
}

function BoomBustRow({
  row,
  rank,
  season,
  scoring,
  maxAbs,
  showGames,
}: {
  row: ProjectionDiffRow;
  rank: number;
  season: number;
  scoring: Scoring;
  maxAbs: number;
  showGames: boolean;
}) {
  const isOver = row.diff >= 0;
  const pct = Math.round((Math.abs(row.diff) / maxAbs) * 100);

  return (
    <tr className="border-t border-slate-800/60 transition-colors hover:bg-slate-900/40">
      <td className="px-3 py-2 text-xs text-slate-600 tabular-nums">{rank}</td>
      <td className="px-3 py-2">
        <Link
          href={`/fantasy/player/${row.gsis_id}?season=${season}&scoring=${scoring}`}
          className="flex items-center gap-2 font-medium text-slate-100 transition-colors hover:text-sky-300"
        >
          <span
            className={`shrink-0 text-[11px] font-semibold ${POSITION_COLORS[row.position] ?? "text-slate-500"}`}
          >
            {row.position}
          </span>
          <span className="truncate">{row.name}</span>
          {row.team && <span className="shrink-0 text-[11px] text-slate-600">{row.team}</span>}
        </Link>
        <div className="mt-0.5 pl-[26px] text-[11px] text-slate-600 sm:hidden">
          proj {row.projected.toFixed(1)} → act {row.actual.toFixed(1)}
          {showGames && ` (${row.games} gm${row.games === 1 ? "" : "s"})`}
        </div>
      </td>
      <td className="hidden px-2 py-2 text-right text-xs text-slate-500 tabular-nums sm:table-cell">
        {row.projected.toFixed(1)}
      </td>
      <td className="hidden px-2 py-2 text-right text-xs text-slate-300 tabular-nums sm:table-cell">
        {row.actual.toFixed(1)}
      </td>
      {showGames && (
        <td className="hidden px-2 py-2 text-right text-xs text-slate-500 tabular-nums sm:table-cell">
          {row.games}
        </td>
      )}
      <td className="px-3 py-2 text-right">
        <div className={`font-semibold tabular-nums ${isOver ? "text-emerald-400" : "text-rose-400"}`}>
          {fmtDiff(row.diff)}
        </div>
        <div className="mt-1 ml-auto h-1 w-16 overflow-hidden rounded-full bg-slate-800">
          <div
            className={`h-full rounded-full ${isOver ? "bg-emerald-500/70" : "bg-rose-500/70"}`}
            style={{ width: `${pct}%`, marginLeft: isOver ? "0" : "auto" }}
          />
        </div>
      </td>
    </tr>
  );
}
