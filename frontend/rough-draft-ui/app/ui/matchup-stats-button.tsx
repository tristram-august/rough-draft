"use client";

import * as React from "react";
import { createPortal } from "react-dom";
import { useQuery } from "@tanstack/react-query";
import { Segmented } from "./segmented";
import { teamColor } from "../lib/team-colors";
import { fetchMatchupStats, type MatchupStatRow } from "../lib/matchup-stats";

/**
 * Each category holds two rows per stat when both perspectives were scraped —
 * one where `team` owns "Points/Game" (their offense) and one where the other
 * team owns it (their offense vs. this team's defense). Grouping by stat_label
 * shows both crossovers together instead of as two unrelated-looking rows.
 */
function groupByStat(rows: MatchupStatRow[]): { label: string; lines: MatchupStatRow[] }[] {
  const order: string[] = [];
  const byLabel = new Map<string, MatchupStatRow[]>();
  for (const row of rows) {
    if (!byLabel.has(row.stat_label)) {
      byLabel.set(row.stat_label, []);
      order.push(row.stat_label);
    }
    byLabel.get(row.stat_label)!.push(row);
  }
  return order.map((label) => ({ label, lines: byLabel.get(label)! }));
}

function StatLine({ row }: { row: MatchupStatRow }) {
  const teamHighlight = row.team_favored === true;
  const oppHighlight = row.team_favored === false;

  return (
    <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 py-1 text-sm">
      <span
        className={`justify-self-end text-right tabular-nums ${
          teamHighlight ? "font-semibold text-slate-100" : "text-slate-400"
        }`}
      >
        <span
          className="mr-1.5 rounded px-1 py-0.5 text-[10px] font-semibold"
          style={{ backgroundColor: `${teamColor(row.team)}33`, color: teamColor(row.team) }}
        >
          {row.team}
        </span>
        {row.team_value}
        {row.team_rank != null && <span className="ml-1 text-[11px] text-slate-600">#{row.team_rank}</span>}
      </span>

      <span aria-hidden className="text-slate-700">
        ·
      </span>

      <span
        className={`justify-self-start tabular-nums ${
          oppHighlight ? "font-semibold text-slate-100" : "text-slate-400"
        }`}
      >
        {row.opp_value}
        {row.opp_rank != null && <span className="ml-1 text-[11px] text-slate-600">#{row.opp_rank}</span>}
        <span
          className="ml-1.5 rounded px-1 py-0.5 text-[10px] font-semibold"
          style={{ backgroundColor: `${teamColor(row.opp_team)}33`, color: teamColor(row.opp_team) }}
        >
          {row.opp_team}
        </span>
      </span>
    </div>
  );
}

function CategoryPanel({ rows }: { rows: MatchupStatRow[] }) {
  const groups = groupByStat(rows);
  return (
    <div className="divide-y divide-slate-800/60">
      {groups.map((g) => (
        <div key={g.label} className="py-2">
          <div className="mb-0.5 text-center text-[11px] font-medium uppercase tracking-wide text-slate-500">
            {g.label}
          </div>
          {g.lines.map((row) => (
            <StatLine key={`${row.team}-${row.stat_label}`} row={row} />
          ))}
        </div>
      ))}
    </div>
  );
}

export function MatchupStatsButton({
  gameId,
  awayTeam,
  homeTeam,
  awayName,
  homeName,
}: {
  gameId: string;
  awayTeam: string;
  homeTeam: string;
  awayName: string | null;
  homeName: string | null;
}) {
  const [open, setOpen] = React.useState(false);
  const [mounted, setMounted] = React.useState(false);
  const [tab, setTab] = React.useState(0);

  React.useEffect(() => setMounted(true), []);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["matchup-stats", gameId],
    queryFn: () => fetchMatchupStats(gameId),
    enabled: open,
  });

  React.useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const categories = data?.categories ?? [];
  const active = categories[tab] ?? categories[0];

  const overlay =
    open && mounted
      ? createPortal(
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Matchup comparison"
            className="fixed inset-0 z-[120] flex flex-col bg-slate-950/95 backdrop-blur-sm"
          >
            <div className="flex shrink-0 items-center justify-between gap-3 border-b border-slate-800 px-4 py-2.5">
              <span className="truncate text-sm font-semibold text-slate-200">
                {awayName ?? awayTeam} @ {homeName ?? homeTeam}
                {data?.source_season && (
                  <span className="ml-2 text-xs font-normal text-slate-500">{data.source_season} season</span>
                )}
              </span>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1 text-xs font-medium text-slate-100 transition-colors hover:bg-slate-700"
              >
                Close
              </button>
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto">
              <div className="mx-auto max-w-lg px-4 py-4">
                {isLoading && <p className="py-10 text-center text-sm text-slate-500">Loading…</p>}
                {isError && (
                  <p className="py-10 text-center text-sm text-red-300">Couldn&apos;t load matchup stats.</p>
                )}
                {data && categories.length === 0 && (
                  <p className="py-10 text-center text-sm text-slate-500">
                    No matchup data for this game yet.
                  </p>
                )}

                {categories.length > 0 && (
                  <>
                    <div className="mb-4 flex justify-center">
                      <Segmented
                        ariaLabel="Stat category"
                        value={String(tab)}
                        onChange={(v) => setTab(Number(v))}
                        options={categories.map((c, i) => ({ value: String(i), label: c.category }))}
                      />
                    </div>
                    {active && <CategoryPanel rows={active.rows} />}
                  </>
                )}
              </div>
            </div>
          </div>,
          document.body
        )
      : null;

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="rounded-lg border border-slate-700 bg-slate-900/60 px-2.5 py-1 text-[11px] font-medium text-slate-300 transition-colors hover:border-slate-600 hover:bg-slate-800"
      >
        Matchup
      </button>
      {overlay}
    </>
  );
}
