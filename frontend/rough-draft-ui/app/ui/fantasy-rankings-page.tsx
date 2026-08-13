"use client";

import * as React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "./page-header";
import { Segmented } from "./segmented";
import { FantasyBoard } from "./fantasy-board";
import { ProjectionsTable } from "./projections-table";
import { CompareTool } from "./compare-tool";
import {
  POSITIONS,
  SCORING_LABELS,
  fetchBoardSeasons,
  fetchFantasySeasons,
  fetchFantasyWeeks,
  fetchLeaderboard,
  type FantasyLeaderRow,
  type FantasyPosition,
  type FantasySort,
  type Scoring,
  type SortDirection,
} from "../lib/fantasy";

const DEFAULT_SORT: FantasySort = "total";

type Column = {
  key: string;
  label: string;
  sortKey: FantasySort;
  value: (row: FantasyLeaderRow) => number;
};

function columnsFor(position: FantasyPosition): Column[] {
  const s = (row: FantasyLeaderRow) => row.stats;
  switch (position) {
    case "QB":
      return [
        { key: "payd", label: "Pa Yd", sortKey: "pass_yards", value: (r) => s(r).pass_yards },
        { key: "patd", label: "Pa TD", sortKey: "pass_tds", value: (r) => s(r).pass_tds },
        { key: "int", label: "INT", sortKey: "pass_ints", value: (r) => s(r).pass_ints },
        { key: "ruyd", label: "Ru Yd", sortKey: "rush_yards", value: (r) => s(r).rush_yards },
        { key: "rutd", label: "Ru TD", sortKey: "rush_tds", value: (r) => s(r).rush_tds },
      ];
    case "RB":
      return [
        { key: "ruyd", label: "Ru Yd", sortKey: "rush_yards", value: (r) => s(r).rush_yards },
        { key: "rutd", label: "Ru TD", sortKey: "rush_tds", value: (r) => s(r).rush_tds },
        { key: "rec", label: "Rec", sortKey: "receptions", value: (r) => s(r).receptions },
        { key: "reyd", label: "Re Yd", sortKey: "rec_yards", value: (r) => s(r).rec_yards },
        { key: "retd", label: "Re TD", sortKey: "rec_tds", value: (r) => s(r).rec_tds },
      ];
    case "WR":
    case "TE":
      return [
        { key: "rec", label: "Rec", sortKey: "receptions", value: (r) => s(r).receptions },
        { key: "reyd", label: "Re Yd", sortKey: "rec_yards", value: (r) => s(r).rec_yards },
        { key: "retd", label: "Re TD", sortKey: "rec_tds", value: (r) => s(r).rec_tds },
        { key: "ruyd", label: "Ru Yd", sortKey: "rush_yards", value: (r) => s(r).rush_yards },
        { key: "rutd", label: "Ru TD", sortKey: "rush_tds", value: (r) => s(r).rush_tds },
      ];
    default:
      return [
        { key: "payd", label: "Pa Yd", sortKey: "pass_yards", value: (r) => s(r).pass_yards },
        { key: "ruyd", label: "Ru Yd", sortKey: "rush_yards", value: (r) => s(r).rush_yards },
        { key: "rec", label: "Rec", sortKey: "receptions", value: (r) => s(r).receptions },
        { key: "reyd", label: "Re Yd", sortKey: "rec_yards", value: (r) => s(r).rec_yards },
        {
          key: "td",
          label: "TD",
          sortKey: "td",
          value: (r) => s(r).pass_tds + s(r).rush_tds + s(r).rec_tds,
        },
      ];
  }
}

const POSITION_COLORS: Record<string, string> = {
  QB: "text-rose-400",
  RB: "text-emerald-400",
  WR: "text-sky-400",
  TE: "text-amber-400",
};

/**
 * Header cell that cycles sort state on click: descending → ascending → off.
 * `active` is null when this column isn't the current sort.
 */
function SortHeader({
  label,
  sortKey,
  activeSort,
  direction,
  onSort,
  align = "right",
  className = "",
}: {
  label: string;
  sortKey: FantasySort;
  activeSort: FantasySort | null;
  direction: SortDirection;
  onSort: (key: FantasySort) => void;
  align?: "left" | "right";
  className?: string;
}) {
  const active = activeSort === sortKey;
  const arrow = active ? (direction === "desc" ? "▼" : "▲") : "▾";

  return (
    <th
      scope="col"
      aria-sort={active ? (direction === "desc" ? "descending" : "ascending") : "none"}
      className={`px-2 py-2.5 font-semibold ${align === "left" ? "text-left" : "text-right"} ${className}`}
    >
      <button
        type="button"
        onClick={() => onSort(sortKey)}
        title={
          active
            ? direction === "desc"
              ? `Sort ${label} ascending`
              : `Clear ${label} sort`
            : `Sort by ${label}`
        }
        className={`group inline-flex items-center gap-1 transition-colors ${
          align === "left" ? "" : "flex-row-reverse"
        } ${active ? "text-slate-100" : "text-slate-500 hover:text-slate-300"}`}
      >
        <span>{label}</span>
        <span
          aria-hidden
          className={`text-[9px] leading-none transition-opacity ${
            active ? "opacity-100" : "opacity-0 group-hover:opacity-60"
          }`}
        >
          {arrow}
        </span>
      </button>
    </th>
  );
}

export default function FantasyRankingsPage({
  initialBoardSeasons,
  initialProductionSeasons,
}: {
  initialBoardSeasons?: number[];
  initialProductionSeasons?: number[];
} = {}) {
  const [tab, setTab] = React.useState<"board" | "leaderboard" | "projections" | "compare">("board");
  const [season, setSeason] = React.useState<number | null>(null);
  const [week, setWeek] = React.useState<number | null>(null);
  const [position, setPosition] = React.useState<FantasyPosition>("ALL");
  const [scoring, setScoring] = React.useState<Scoring>("ppr");

  // null = no explicit sort; falls back to the default ordering.
  const [sort, setSort] = React.useState<FantasySort | null>(null);
  const [direction, setDirection] = React.useState<SortDirection>("desc");

  const effectiveSort = sort ?? DEFAULT_SORT;
  const effectiveDirection: SortDirection = sort === null ? "desc" : direction;

  function handleSort(key: FantasySort) {
    if (sort !== key) {
      setSort(key);
      setDirection("desc");
      return;
    }
    if (direction === "desc") {
      setDirection("asc");
      return;
    }
    // Third click clears back to the default ordering.
    setSort(null);
    setDirection("desc");
  }

  const seasonsQuery = useQuery({
    queryKey: ["fantasy-seasons"],
    queryFn: fetchFantasySeasons,
    initialData: initialProductionSeasons,
  });
  const boardSeasonsQuery = useQuery({
    queryKey: ["fantasy-board-seasons"],
    queryFn: fetchBoardSeasons,
    initialData: initialBoardSeasons,
  });

  const boardSeasons = React.useMemo(() => boardSeasonsQuery.data ?? [], [boardSeasonsQuery.data]);

  // Board seasons (upcoming, pre-snap) sit above production seasons (what happened).
  const seasons = React.useMemo(() => {
    const merged = [...new Set([...boardSeasons, ...(seasonsQuery.data ?? [])])];
    return merged.sort((a, b) => b - a);
  }, [boardSeasons, seasonsQuery.data]);

  // Default to the draft board — it's the forward-looking view.
  const activeSeason = season ?? seasons[0] ?? null;
  // Availability checks per tab, not a view-selector — season is now a shared
  // filter across all four tabs (Board/Leaderboard/Projections/Compare), not
  // the thing that decides which one renders.
  const boardAvailable = activeSeason != null && boardSeasons.includes(activeSeason);
  const productionAvailable = activeSeason != null && (seasonsQuery.data?.includes(activeSeason) ?? false);

  const weeksQuery = useQuery({
    queryKey: ["fantasy-weeks", activeSeason],
    queryFn: () => fetchFantasyWeeks(activeSeason as number),
    enabled: activeSeason != null && tab === "leaderboard",
  });

  // Per-game sorting needs a games floor, or one-game samples top the board.
  const minGames = effectiveSort === "ppg" && week == null ? 4 : 1;

  const boardQuery = useQuery({
    queryKey: [
      "fantasy-leaderboard",
      activeSeason,
      week,
      position,
      scoring,
      effectiveSort,
      effectiveDirection,
      minGames,
    ],
    queryFn: () =>
      fetchLeaderboard({
        season: activeSeason as number,
        week,
        position,
        scoring,
        sort: effectiveSort,
        direction: effectiveDirection,
        minGames,
        limit: 100,
      }),
    enabled: activeSeason != null && tab === "leaderboard",
    placeholderData: (prev) => prev,
  });

  const columns = columnsFor(position);
  const rows = boardQuery.data?.rows ?? [];
  const weeks = weeksQuery.data ?? [];

  const selectClass =
    "rounded-xl border border-slate-800 bg-slate-900/40 px-3 py-1.5 text-xs font-medium text-slate-300 outline-none transition-colors focus:border-slate-600";

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <PageHeader
        eyebrow="Fantasy Draft"
        title={
          tab === "board"
            ? `${activeSeason} Draft Board`
            : tab === "leaderboard"
            ? "Production Rankings"
            : tab === "projections"
            ? "Projections"
            : "Compare Players"
        }
        subtitle={
          tab === "board"
            ? "Preseason consensus ranks for the upcoming draft. Switch the year to see what actually happened."
            : tab === "leaderboard"
            ? "Fantasy points computed from game-by-game production. Switch scoring to match your league."
            : tab === "projections"
            ? "FantasyPros' own weekly and rest-of-season point projections."
            : "See how individual experts rank players against each other, live."
        }
      />

      {/* Filters */}
      <div className="mb-5 flex flex-wrap items-center gap-2">
        <Segmented
          ariaLabel="View"
          value={tab}
          onChange={setTab}
          options={[
            { value: "board", label: "Board" },
            { value: "leaderboard", label: "Leaderboard" },
            { value: "projections", label: "Projections" },
            { value: "compare", label: "Compare" },
          ]}
        />
        <select
          aria-label="Season"
          value={activeSeason ?? ""}
          onChange={(e) => {
            setSeason(Number(e.target.value));
            setWeek(null);
          }}
          className={selectClass}
        >
          {seasons.map((s) => (
            <option key={s} value={s}>
              {s}
              {boardSeasons.includes(s) ? " — Draft Board" : ""}
            </option>
          ))}
        </select>
      </div>

      {tab === "board" && (
        boardAvailable && activeSeason != null ? (
          <FantasyBoard season={activeSeason} />
        ) : (
          <p className="text-sm text-slate-500">No draft board loaded for {activeSeason}.</p>
        )
      )}

      {tab === "projections" && activeSeason != null && <ProjectionsTable season={activeSeason} />}

      {tab === "compare" && (
        boardAvailable && activeSeason != null ? (
          <CompareTool season={activeSeason} />
        ) : (
          <p className="text-sm text-slate-500">
            No draft board loaded for {activeSeason} to compare from.
          </p>
        )
      )}

      {/* Production rankings */}
      {tab === "leaderboard" && !productionAvailable && (
        <p className="text-sm text-slate-500">No production data for {activeSeason} yet.</p>
      )}
      {tab === "leaderboard" && productionAvailable && (
        <>
      <div className="mb-5 flex flex-wrap items-center gap-2">
        <Segmented
          ariaLabel="Scoring format"
          value={scoring}
          onChange={setScoring}
          options={(["ppr", "half", "std"] as const).map((k) => ({
            value: k,
            label: SCORING_LABELS[k],
          }))}
        />

        <select
          aria-label="Week"
          value={week ?? ""}
          onChange={(e) => setWeek(e.target.value === "" ? null : Number(e.target.value))}
          className={selectClass}
        >
          <option value="">Full season</option>
          {weeks.map((w) => (
            <option key={w} value={w}>
              Week {w}
            </option>
          ))}
        </select>

        <Segmented
          ariaLabel="Position"
          value={position}
          onChange={setPosition}
          options={POSITIONS.map((p) => ({ value: p, label: p === "ALL" ? "All" : p }))}
        />

        {minGames > 1 && <span className="text-xs text-slate-600">min {minGames} games</span>}

        {sort !== null && (
          <button
            type="button"
            onClick={() => {
              setSort(null);
              setDirection("desc");
            }}
            className="rounded-lg border border-slate-800 px-2.5 py-1 text-xs text-slate-500 transition-colors hover:text-slate-300"
          >
            Clear sort ×
          </button>
        )}
      </div>

      {boardQuery.isError && (
        <div className="rounded-2xl border border-red-900/40 bg-red-950/20 px-4 py-3 text-sm text-red-300">
          Couldn&apos;t load rankings. Try again in a moment.
        </div>
      )}

      {boardQuery.isLoading && <p className="text-sm text-slate-500">Loading…</p>}

      {boardQuery.data && rows.length === 0 && (
        <p className="text-sm text-slate-500">No players match those filters.</p>
      )}

      {rows.length > 0 && (
        <div
          className={`overflow-x-auto rounded-3xl border border-slate-800 transition-opacity ${
            boardQuery.isFetching ? "opacity-60" : ""
          }`}
        >
          <table className="w-full sm:min-w-[560px] border-collapse text-sm">
            <thead className="bg-slate-900/60">
              <tr className="text-xs uppercase tracking-wide text-slate-500">
                <th scope="col" className="px-3 py-2.5 text-left font-semibold">
                  #
                </th>
                <SortHeader
                  label="Player"
                  sortKey="name"
                  activeSort={sort}
                  direction={direction}
                  onSort={handleSort}
                  align="left"
                  className="pl-3"
                />
                <SortHeader
                  label="G"
                  sortKey="games"
                  activeSort={sort}
                  direction={direction}
                  onSort={handleSort}
                />
                <SortHeader
                  label="Pts"
                  sortKey="total"
                  activeSort={sort}
                  direction={direction}
                  onSort={handleSort}
                  className="pr-3"
                />
                <SortHeader
                  label="PPG"
                  sortKey="ppg"
                  activeSort={sort}
                  direction={direction}
                  onSort={handleSort}
                  className="pr-3"
                />
                {columns.map((c) => (
                  <SortHeader
                    key={c.key}
                    label={c.label}
                    sortKey={c.sortKey}
                    activeSort={sort}
                    direction={direction}
                    onSort={handleSort}
                    className="hidden sm:table-cell"
                  />
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr
                  key={row.gsis_id}
                  className="border-t border-slate-800/60 transition-colors hover:bg-slate-900/40"
                >
                  <td className="px-3 py-2 text-xs text-slate-600 tabular-nums">{row.rank}</td>
                  <td className="px-3 py-2">
                    <Link
                      href={`/fantasy/player/${row.gsis_id}?season=${activeSeason}&scoring=${scoring}`}
                      className="flex items-center gap-2 font-medium text-slate-100 transition-colors hover:text-sky-300"
                    >
                      <span className="truncate">{row.name}</span>
                      {row.position && (
                        <span
                          className={`shrink-0 text-[11px] font-semibold ${
                            POSITION_COLORS[row.position] ?? "text-slate-500"
                          }`}
                        >
                          {row.position}
                        </span>
                      )}
                      {row.team && (
                        <span className="shrink-0 text-[11px] text-slate-600">{row.team}</span>
                      )}
                    </Link>
                  </td>
                  <td className="px-2 py-2 text-right text-xs text-slate-500 tabular-nums">
                    {row.games}
                  </td>
                  <td className="px-3 py-2 text-right font-semibold text-slate-100 tabular-nums">
                    {row.fantasy_points.toFixed(1)}
                  </td>
                  <td className="px-3 py-2 text-right text-slate-400 tabular-nums">
                    {row.points_per_game.toFixed(1)}
                  </td>
                  {columns.map((c) => (
                    <td
                      key={c.key}
                      className="hidden px-2 py-2 text-right text-xs text-slate-500 tabular-nums sm:table-cell"
                    >
                      {c.value(row)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="mt-4 text-xs leading-relaxed text-slate-600">
        Scoring: 1 pt / 25 passing yards, 4 pts / passing TD, −2 / interception, 1 pt / 10
        rushing or receiving yards, 6 pts / rushing or receiving TD, −2 / fumble lost,{" "}
        {scoring === "ppr" ? "1 pt" : scoring === "half" ? "0.5 pts" : "0 pts"} / reception.
      </p>
        </>
      )}
    </div>
  );
}
