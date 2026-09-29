"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "./page-header";
import { Segmented } from "./segmented";
import {
  fetchTeamSeasons,
  fetchTeamStats,
  fetchTeamWeeks,
  type SortDirection,
  type TeamStatRow,
  type TeamStatSort,
} from "../lib/teams";

type View = "offense" | "defense";

type Column = {
  key: string;
  label: string;
  sortKey: TeamStatSort;
  value: (row: TeamStatRow) => number | null;
  fmt?: (v: number) => string;
};

const OFFENSE_COLUMNS: Column[] = [
  { key: "epap", label: "EPA/Play", sortKey: "off_epa_per_play", value: (r) => r.off_epa_per_play, fmt: (v) => v.toFixed(3) },
  { key: "epa", label: "Total EPA", sortKey: "off_epa", value: (r) => r.off_epa, fmt: (v) => v.toFixed(1) },
  { key: "pf", label: "Points", sortKey: "points_for", value: (r) => r.points_for },
  { key: "payd", label: "Pass Yd", sortKey: "pass_yards", value: (r) => r.pass_yards },
  { key: "patd", label: "Pass TD", sortKey: "pass_tds", value: (r) => r.pass_tds },
  { key: "ruyd", label: "Rush Yd", sortKey: "rush_yards", value: (r) => r.rush_yards },
  { key: "rutd", label: "Rush TD", sortKey: "rush_tds", value: (r) => r.rush_tds },
  { key: "give", label: "Giveaways", sortKey: "giveaways", value: (r) => r.giveaways },
];

const DEFENSE_COLUMNS: Column[] = [
  {
    key: "depap",
    label: "EPA/Play Allowed",
    sortKey: "def_epa_per_play_allowed",
    value: (r) => r.def_epa_per_play_allowed,
    fmt: (v) => v.toFixed(3),
  },
  { key: "depa", label: "EPA Allowed", sortKey: "def_epa_allowed", value: (r) => r.def_epa_allowed, fmt: (v) => v.toFixed(1) },
  { key: "pa", label: "Points Allowed", sortKey: "points_against", value: (r) => r.points_against },
  { key: "sk", label: "Sacks", sortKey: "def_sacks", value: (r) => r.def_sacks, fmt: (v) => v.toFixed(1) },
  { key: "int", label: "INT", sortKey: "def_interceptions", value: (r) => r.def_interceptions },
  { key: "tk", label: "Takeaways", sortKey: "takeaways", value: (r) => r.takeaways },
];

const selectClass =
  "rounded-xl border border-slate-800 bg-slate-900/40 px-3 py-1.5 text-xs font-medium text-slate-300 outline-none transition-colors focus:border-slate-600";

function SortHeader({
  label,
  sortKey,
  activeSort,
  direction,
  onSort,
}: {
  label: string;
  sortKey: TeamStatSort;
  activeSort: TeamStatSort;
  direction: SortDirection;
  onSort: (key: TeamStatSort) => void;
}) {
  const active = activeSort === sortKey;
  const arrow = active ? (direction === "desc" ? "▼" : "▲") : "▾";
  return (
    <th scope="col" aria-sort={active ? (direction === "desc" ? "descending" : "ascending") : "none"} className="px-2 py-2.5 text-right font-semibold">
      <button
        type="button"
        onClick={() => onSort(sortKey)}
        className="group inline-flex flex-row-reverse items-center gap-1 transition-colors hover:text-slate-200"
      >
        {label}
        <span className={`text-[9px] ${active ? "text-slate-300" : "text-slate-700 group-hover:text-slate-500"}`}>{arrow}</span>
      </button>
    </th>
  );
}

export function TeamStatsPage() {
  const [view, setView] = React.useState<View>("offense");
  const [season, setSeason] = React.useState<number | null>(null);
  const [week, setWeek] = React.useState<number | null>(null);
  const [sort, setSort] = React.useState<TeamStatSort | null>(null);
  const [direction, setDirection] = React.useState<SortDirection>("desc");

  const seasonsQuery = useQuery({ queryKey: ["team-seasons"], queryFn: fetchTeamSeasons });
  const seasons = seasonsQuery.data ?? [];
  const activeSeason = season ?? seasons[0] ?? null;

  const weeksQuery = useQuery({
    queryKey: ["team-weeks", activeSeason],
    queryFn: () => fetchTeamWeeks(activeSeason as number),
    enabled: activeSeason != null,
  });
  const weeks = weeksQuery.data ?? [];

  const defaultSort: TeamStatSort = view === "offense" ? "off_epa_per_play" : "def_epa_per_play_allowed";
  const effectiveSort = sort ?? defaultSort;
  // Defense's headline stat is "least allowed," so a fresh switch to that
  // view should default ascending, not desc-for-everything.
  const effectiveDirection: SortDirection = sort === null ? (view === "offense" ? "desc" : "asc") : direction;

  const statsQuery = useQuery({
    queryKey: ["team-stats", activeSeason, week, effectiveSort, effectiveDirection],
    queryFn: () =>
      fetchTeamStats({ season: activeSeason as number, week, sort: effectiveSort, direction: effectiveDirection }),
    enabled: activeSeason != null,
    placeholderData: (prev) => prev,
  });

  function handleSort(key: TeamStatSort) {
    if (sort !== key) {
      setSort(key);
      setDirection("desc");
      return;
    }
    if (direction === "desc") {
      setDirection("asc");
      return;
    }
    setSort(null);
    setDirection("desc");
  }

  const columns = view === "offense" ? OFFENSE_COLUMNS : DEFENSE_COLUMNS;
  const rows = statsQuery.data?.rows ?? [];

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <PageHeader
        eyebrow="Teams"
        title="Team Stats"
        subtitle="Offensive and defensive production by team, from nflverse's play-by-play-derived box scores. EPA/play is the headline number -- expected points added, positive means the unit's outproducing what an average play in that spot would."
      />

      <div className="mb-5 flex flex-wrap items-center gap-2">
        <Segmented ariaLabel="View" value={view} onChange={(v) => { setView(v as View); setSort(null); }} options={[
          { value: "offense", label: "Offense" },
          { value: "defense", label: "Defense" },
        ]} />

        <select
          aria-label="Season"
          value={activeSeason ?? ""}
          onChange={(e) => { setSeason(Number(e.target.value)); setWeek(null); }}
          className={selectClass}
        >
          {seasons.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>

        <select
          aria-label="Week"
          value={week ?? ""}
          onChange={(e) => setWeek(e.target.value === "" ? null : Number(e.target.value))}
          className={selectClass}
        >
          <option value="">Full season</option>
          {weeks.map((w) => (
            <option key={w} value={w}>Week {w}</option>
          ))}
        </select>
      </div>

      {statsQuery.isError && (
        <div className="rounded-2xl border border-red-900/40 bg-red-950/20 px-4 py-3 text-sm text-red-300">
          Couldn&apos;t load team stats. Try again in a moment.
        </div>
      )}

      {statsQuery.isLoading && <p className="text-sm text-slate-500">Loading…</p>}

      {rows.length > 0 && (
        <div className="overflow-x-auto rounded-3xl border border-slate-800">
          <table className="w-full sm:min-w-[720px] border-collapse text-sm">
            <thead className="bg-slate-900/60">
              <tr className="text-xs uppercase tracking-wide text-slate-500">
                <th className="px-3 py-2.5 text-left font-semibold">#</th>
                <th className="px-3 py-2.5 text-left font-semibold">Team</th>
                <th className="px-2 py-2.5 text-right font-semibold">GP</th>
                {columns.map((c) => (
                  <SortHeader
                    key={c.key}
                    label={c.label}
                    sortKey={c.sortKey}
                    activeSort={effectiveSort}
                    direction={effectiveDirection}
                    onSort={handleSort}
                  />
                ))}
                <SortHeader
                  label="TO Margin"
                  sortKey="turnover_margin"
                  activeSort={effectiveSort}
                  direction={effectiveDirection}
                  onSort={handleSort}
                />
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={r.team} className="border-t border-slate-800/60 transition-colors hover:bg-slate-900/40">
                  <td className="px-3 py-2 text-xs text-slate-600 tabular-nums">{i + 1}</td>
                  <td className="px-3 py-2">
                    <span className="font-medium text-slate-100">{r.team_name ?? r.team}</span>
                    <span className="ml-1.5 text-[11px] text-slate-600">{r.team}</span>
                  </td>
                  <td className="px-2 py-2 text-right text-xs text-slate-500 tabular-nums">{r.games}</td>
                  {columns.map((c) => {
                    const v = c.value(r);
                    return (
                      <td key={c.key} className="px-2 py-2 text-right text-xs text-slate-300 tabular-nums">
                        {v == null ? "—" : c.fmt ? c.fmt(v) : v}
                      </td>
                    );
                  })}
                  <td
                    className={`px-2 py-2 text-right text-xs font-semibold tabular-nums ${
                      r.turnover_margin > 0 ? "text-emerald-400" : r.turnover_margin < 0 ? "text-rose-400" : "text-slate-500"
                    }`}
                  >
                    {r.turnover_margin > 0 ? "+" : ""}
                    {r.turnover_margin}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="mt-4 text-xs leading-relaxed text-slate-600">
        Takeaways counts interceptions plus forced fumbles as a proxy -- a forced fumble isn&apos;t always recovered by the forcing team, so it can run slightly high.
      </p>
    </div>
  );
}
