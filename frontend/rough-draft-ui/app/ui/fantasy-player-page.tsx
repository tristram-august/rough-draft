"use client";

import * as React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Segmented } from "./segmented";
import {
  SCORING_LABELS,
  fetchFantasyPlayer,
  type FantasyStatLine,
  type Scoring,
} from "../lib/fantasy";

const POSITION_COLORS: Record<string, string> = {
  QB: "text-rose-400",
  RB: "text-emerald-400",
  WR: "text-sky-400",
  TE: "text-amber-400",
};

/** Only show stat columns the player actually accumulated. */
function relevantColumns(lines: FantasyStatLine[]) {
  const has = (pick: (s: FantasyStatLine) => number) => lines.some((l) => pick(l) !== 0);
  const cols: { label: string; value: (s: FantasyStatLine) => number }[] = [];
  if (has((s) => s.pass_yards) || has((s) => s.pass_tds)) {
    cols.push({ label: "Pa Yd", value: (s) => s.pass_yards });
    cols.push({ label: "Pa TD", value: (s) => s.pass_tds });
    cols.push({ label: "INT", value: (s) => s.pass_ints });
  }
  if (has((s) => s.rush_yards) || has((s) => s.rush_tds)) {
    cols.push({ label: "Ru Yd", value: (s) => s.rush_yards });
    cols.push({ label: "Ru TD", value: (s) => s.rush_tds });
  }
  if (has((s) => s.receptions) || has((s) => s.rec_yards)) {
    cols.push({ label: "Rec", value: (s) => s.receptions });
    cols.push({ label: "Re Yd", value: (s) => s.rec_yards });
    cols.push({ label: "Re TD", value: (s) => s.rec_tds });
  }
  return cols;
}

export default function FantasyPlayerPage({
  gsisId,
  initialSeason,
  initialScoring,
}: {
  gsisId: string;
  initialSeason?: number | null;
  initialScoring?: Scoring;
}) {
  const [scoring, setScoring] = React.useState<Scoring>(initialScoring ?? "ppr");
  const [season, setSeason] = React.useState<number | null>(initialSeason ?? null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["fantasy-player", gsisId, scoring, season],
    queryFn: () => fetchFantasyPlayer(gsisId, scoring, season),
  });

  if (isLoading) {
    return <p className="mx-auto max-w-5xl px-4 py-8 text-sm text-slate-500">Loading…</p>;
  }
  if (isError || !data) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-8">
        <div className="rounded-2xl border border-red-900/40 bg-red-950/20 px-4 py-3 text-sm text-red-300">
          Couldn&apos;t load this player.
        </div>
      </div>
    );
  }

  const seasonCols = relevantColumns(data.seasons.map((s) => s.stats));
  const gameCols = relevantColumns(data.games.map((g) => g.stats));
  const activeSeason = data.games[0]?.season ?? season ?? data.seasons[0]?.season ?? null;
  const bestGame = data.games.reduce<number>((max, g) => Math.max(max, g.fantasy_points), 0);

  const thClass =
    "px-2 py-2.5 text-right text-xs font-semibold uppercase tracking-wide text-slate-500";
  const tdClass = "px-2 py-2 text-right text-xs text-slate-500 tabular-nums";

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <Link
        href="/fantasy"
        className="text-xs font-medium text-slate-500 transition-colors hover:text-slate-300"
      >
        <span aria-hidden>←</span> Fantasy rankings
      </Link>

      <div className="mt-5 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          {data.headshot && (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={data.headshot}
              alt=""
              className="h-16 w-16 rounded-2xl border border-slate-800 bg-slate-900 object-cover"
            />
          )}
          <div>
            <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">{data.name}</h1>
            {data.position && (
              <p
                className={`mt-1 text-sm font-semibold ${
                  POSITION_COLORS[data.position] ?? "text-slate-500"
                }`}
              >
                {data.position}
              </p>
            )}
          </div>
        </div>

        <Segmented
          ariaLabel="Scoring format"
          value={scoring}
          onChange={setScoring}
          options={(["ppr", "half", "std"] as const).map((k) => ({
            value: k,
            label: SCORING_LABELS[k],
          }))}
        />
      </div>

      {/* Season-by-season */}
      <h2 className="mt-10 mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">
        By season
      </h2>
      {data.seasons.length === 0 ? (
        <p className="text-sm text-slate-500">No regular season stats on record.</p>
      ) : (
        <div className="overflow-x-auto rounded-3xl border border-slate-800">
          <table className="w-full min-w-[520px] border-collapse text-sm">
            <thead className="bg-slate-900/60">
              <tr>
                <th className="px-3 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Season
                </th>
                <th className="px-2 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Team
                </th>
                <th className={thClass}>G</th>
                <th className={`${thClass} text-slate-300`}>Pts</th>
                <th className={thClass}>PPG</th>
                {seasonCols.map((c) => (
                  <th key={c.label} className={`${thClass} hidden sm:table-cell`}>
                    {c.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.seasons.map((s) => (
                <tr
                  key={s.season}
                  className={`border-t border-slate-800/60 transition-colors hover:bg-slate-900/40 ${
                    s.season === activeSeason ? "bg-slate-900/30" : ""
                  }`}
                >
                  <td className="px-3 py-2">
                    <button
                      type="button"
                      onClick={() => setSeason(s.season)}
                      className="font-medium text-slate-100 transition-colors hover:text-sky-300"
                    >
                      {s.season}
                    </button>
                  </td>
                  <td className="px-2 py-2 text-xs text-slate-500">{s.team ?? "—"}</td>
                  <td className={tdClass}>{s.games}</td>
                  <td className="px-2 py-2 text-right text-sm font-semibold text-slate-100 tabular-nums">
                    {s.fantasy_points.toFixed(1)}
                  </td>
                  <td className="px-2 py-2 text-right text-sm text-slate-400 tabular-nums">
                    {s.points_per_game.toFixed(1)}
                  </td>
                  {seasonCols.map((c) => (
                    <td key={c.label} className={`${tdClass} hidden sm:table-cell`}>
                      {c.value(s.stats)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Game log */}
      {data.games.length > 0 && (
        <>
          <h2 className="mt-10 mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">
            {activeSeason} game log
          </h2>
          <div className="overflow-x-auto rounded-3xl border border-slate-800">
            <table className="w-full min-w-[520px] border-collapse text-sm">
              <thead className="bg-slate-900/60">
                <tr>
                  <th className="px-3 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Wk
                  </th>
                  <th className="px-2 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Opp
                  </th>
                  <th className={`${thClass} text-slate-300`}>Pts</th>
                  {gameCols.map((c) => (
                    <th key={c.label} className={`${thClass} hidden sm:table-cell`}>
                      {c.label}
                    </th>
                  ))}
                  <th className="w-24 px-3 py-2.5" />
                </tr>
              </thead>
              <tbody>
                {data.games.map((g) => (
                  <tr key={`${g.season}-${g.week}`} className="border-t border-slate-800/60">
                    <td className="px-3 py-2 text-xs text-slate-400 tabular-nums">{g.week ?? "—"}</td>
                    <td className="px-2 py-2 text-xs text-slate-500">{g.opponent ?? "—"}</td>
                    <td className="px-2 py-2 text-right text-sm font-semibold text-slate-100 tabular-nums">
                      {g.fantasy_points.toFixed(1)}
                    </td>
                    {gameCols.map((c) => (
                      <td key={c.label} className={`${tdClass} hidden sm:table-cell`}>
                        {c.value(g.stats)}
                      </td>
                    ))}
                    <td className="px-3 py-2">
                      {/* Bar scaled against this player's best game */}
                      <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
                        <div
                          className="h-full rounded-full bg-sky-500/70"
                          style={{
                            width: `${
                              bestGame > 0
                                ? Math.max(0, (g.fantasy_points / bestGame) * 100)
                                : 0
                            }%`,
                          }}
                        />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
