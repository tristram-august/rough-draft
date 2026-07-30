"use client";

import * as React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Segmented } from "./segmented";
import { fetchBoard, type FantasyBoardRow } from "../lib/fantasy";

const POSITION_COLORS: Record<string, string> = {
  QB: "text-rose-400",
  RB: "text-emerald-400",
  WR: "text-sky-400",
  TE: "text-amber-400",
  K: "text-slate-400",
  DST: "text-violet-400",
};

/** Strength of schedule runs 0–5; 5 is the easiest slate. */
function SosPips({ sos }: { sos: number | null }) {
  if (sos == null) return <span className="text-slate-700">—</span>;
  return (
    <span className="inline-flex gap-0.5" title={`Strength of schedule ${sos}/5`}>
      {[1, 2, 3, 4, 5].map((n) => (
        <span
          key={n}
          className={`h-1.5 w-1.5 rounded-full ${
            n <= sos ? "bg-emerald-500/70" : "bg-slate-800"
          }`}
        />
      ))}
    </span>
  );
}

function ValueBadge({ value }: { value: number | null }) {
  if (value == null) return <span className="text-slate-700">—</span>;
  if (value === 0) return <span className="text-slate-600 tabular-nums">even</span>;
  // Positive means ECR is ahead of ADP — available later than he's ranked.
  const positive = value > 0;
  return (
    <span className={`tabular-nums ${positive ? "text-emerald-400" : "text-rose-400"}`}>
      {positive ? "+" : ""}
      {value}
    </span>
  );
}

export function FantasyBoard({ season }: { season: number }) {
  const [position, setPosition] = React.useState("ALL");

  const { data, isLoading, isError } = useQuery({
    queryKey: ["fantasy-board", season, position],
    queryFn: () => fetchBoard(season, position, 400),
    placeholderData: (prev) => prev,
  });

  const rows = data?.rows ?? [];
  const positionOptions = ["ALL", ...(data?.positions ?? [])];

  if (isError) {
    return (
      <div className="rounded-2xl border border-red-900/40 bg-red-950/20 px-4 py-3 text-sm text-red-300">
        Couldn&apos;t load the {season} draft board.
      </div>
    );
  }

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-center gap-2">
        <Segmented
          ariaLabel="Position"
          value={position}
          onChange={setPosition}
          options={positionOptions.map((p) => ({ value: p, label: p === "ALL" ? "All" : p }))}
        />
        {data && (
          <span className="text-xs text-slate-600">
            {data.total} player{data.total === 1 ? "" : "s"}
          </span>
        )}
      </div>

      {isLoading && <p className="text-sm text-slate-500">Loading…</p>}

      {data && rows.length === 0 && (
        <p className="text-sm text-slate-500">No players at that position.</p>
      )}

      {rows.length > 0 && (
        <div className="overflow-x-auto rounded-3xl border border-slate-800">
          <table className="w-full min-w-[620px] border-collapse text-sm">
            <thead className="bg-slate-900/60">
              <tr className="text-xs uppercase tracking-wide text-slate-500">
                <th className="px-3 py-2.5 text-left font-semibold">#</th>
                <th className="px-3 py-2.5 text-left font-semibold">Player</th>
                <th className="px-2 py-2.5 text-left font-semibold">Pos</th>
                <th className="px-2 py-2.5 text-left font-semibold">Team</th>
                <th className="px-2 py-2.5 text-right font-semibold">Bye</th>
                <th className="hidden px-2 py-2.5 text-left font-semibold sm:table-cell">SoS</th>
                <th
                  className="hidden px-2 py-2.5 text-right font-semibold sm:table-cell"
                  title="ECR vs ADP — positive means he lasts later than he's ranked"
                >
                  vs ADP
                </th>
                <th className="hidden px-3 py-2.5 text-right font-semibold sm:table-cell">
                  Avg diff
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => {
                const prev: FantasyBoardRow | undefined = rows[i - 1];
                const startsTier = row.tier != null && prev?.tier !== row.tier;
                return (
                  <React.Fragment key={`${row.overall_rank}-${row.player_name}`}>
                    {startsTier && (
                      <tr>
                        <td
                          colSpan={8}
                          className="border-t border-slate-800 bg-slate-900/40 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500"
                        >
                          Tier {row.tier}
                        </td>
                      </tr>
                    )}
                    <tr className="border-t border-slate-800/60 transition-colors hover:bg-slate-900/40">
                      <td className="px-3 py-2 text-xs text-slate-600 tabular-nums">
                        {row.overall_rank}
                      </td>
                      <td className="px-3 py-2">
                        {row.gsis_id ? (
                          <Link
                            href={`/fantasy/player/${row.gsis_id}?scoring=ppr`}
                            className="font-medium text-slate-100 transition-colors hover:text-sky-300"
                            title="See production history"
                          >
                            {row.player_name}
                          </Link>
                        ) : (
                          <span className="font-medium text-slate-100">{row.player_name}</span>
                        )}
                      </td>
                      <td className="px-2 py-2">
                        <span
                          className={`text-[11px] font-semibold ${
                            POSITION_COLORS[row.position] ?? "text-slate-500"
                          }`}
                        >
                          {row.position}
                          {row.position_rank != null && (
                            <span className="text-slate-600">{row.position_rank}</span>
                          )}
                        </span>
                      </td>
                      <td className="px-2 py-2 text-xs text-slate-500">{row.team ?? "—"}</td>
                      <td className="px-2 py-2 text-right text-xs text-slate-500 tabular-nums">
                        {row.bye_week ?? "—"}
                      </td>
                      <td className="hidden px-2 py-2 sm:table-cell">
                        <SosPips sos={row.sos} />
                      </td>
                      <td className="hidden px-2 py-2 text-right text-xs sm:table-cell">
                        <ValueBadge value={row.ecr_vs_adp} />
                      </td>
                      <td className="hidden px-3 py-2 text-right text-xs text-slate-500 tabular-nums sm:table-cell">
                        {row.avg_diff ?? "—"}
                      </td>
                    </tr>
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <p className="mt-4 text-xs leading-relaxed text-slate-600">
        Preseason consensus board. <span className="text-slate-500">vs ADP</span> is expert
        consensus rank minus average draft position — positive means he tends to last longer
        than he&apos;s ranked. Names link to production history where we could match the player.
      </p>
    </div>
  );
}
