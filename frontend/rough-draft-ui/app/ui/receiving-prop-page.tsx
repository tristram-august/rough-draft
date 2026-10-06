"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import {
  GAME_LOG_COLUMNS,
  GROUP_LABELS,
  GROUP_NOUN,
  STAT_OPTIONS,
  fetchBettingPlayers,
  fetchCalibration,
  fetchPlayerProp,
  fetchUpcomingWeek,
  type StatGroup,
  type StatKey,
} from "../lib/betting";

const DEFAULT_SEASON = 2026;
const MATCH_LIMIT = 20;
const COUNT_STATS: StatKey[] = ["rec_tds", "pass_tds", "interceptions", "rush_tds"];

function pct(p: number) {
  return `${Math.round(p * 100)}%`;
}

function fmtOrDash(value: number | null, digits: number, asPct = false) {
  if (value == null) return "—";
  return asPct ? pct(value) : value.toFixed(digits);
}

const VOLUME_LABEL: Record<StatGroup, string> = {
  receiving: "Targets",
  rushing: "Carries",
  passing: "Pass attempts",
};

export default function ReceivingPropPage() {
  const season = DEFAULT_SEASON;
  const [query, setQuery] = React.useState("");
  const [selected, setSelected] = React.useState<string | null>(null);
  const [stat, setStat] = React.useState<StatKey>("rec_yards");
  const [line, setLine] = React.useState<number | null>(null);
  const [showCalibration, setShowCalibration] = React.useState(false);

  const statOption = STAT_OPTIONS.find((o) => o.key === stat) ?? STAT_OPTIONS[0];
  const group = statOption.group;
  const unit = statOption.unit;
  const isCount = COUNT_STATS.includes(stat);

  const upcomingQuery = useQuery({
    queryKey: ["betting-upcoming-week", season],
    queryFn: () => fetchUpcomingWeek(season),
  });
  const upcomingWeek = upcomingQuery.data?.week ?? null;

  const playersQuery = useQuery({
    queryKey: ["betting-players", season, group],
    queryFn: () => fetchBettingPlayers(season, group),
  });

  const matches = React.useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q || !playersQuery.data) return [];
    return playersQuery.data.filter((r) => r.name.toLowerCase().includes(q)).slice(0, MATCH_LIMIT);
  }, [query, playersQuery.data]);

  const propQuery = useQuery({
    queryKey: ["player-prop", selected, season, upcomingWeek, stat],
    queryFn: () => fetchPlayerProp(selected as string, season, upcomingWeek as number, stat),
    enabled: selected != null && upcomingWeek != null,
    retry: false,
  });
  const prop = propQuery.data;

  const calibrationQuery = useQuery({
    queryKey: ["betting-calibration", season, stat],
    queryFn: () => fetchCalibration(season, stat),
    staleTime: 10 * 60 * 1000,
  });
  const calibration = calibrationQuery.data;

  React.useEffect(() => {
    setSelected(null);
    setQuery("");
  }, [group]);

  React.useEffect(() => {
    setLine(null);
  }, [selected, stat]);

  const statLabel = statOption.label;
  const defaultLine = prop ? (isCount ? 1 : Math.round(prop.mean)) : 0;
  const shownLine = Math.min(line ?? defaultLine, prop?.line_max ?? 150);
  const pOver = prop?.distribution[shownLine]?.p_over ?? null;
  const meanDigits = isCount ? 2 : 1;

  return (
    <div className="mx-auto max-w-5xl space-y-6 px-4 py-8">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-400">Player Props</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight">Player props</h1>
        <p className="mt-2 text-sm text-slate-400">
          Pick a player and a stat, then move the line to see how likely they are to clear it, based on
          their game-by-game history and the opponent&apos;s defense.
        </p>
      </div>

      <div className="flex flex-wrap gap-2" role="group" aria-label="Stat">
        {STAT_OPTIONS.map((o) => (
          <button
            key={o.key}
            type="button"
            onClick={() => setStat(o.key)}
            aria-pressed={stat === o.key}
            className={`rounded-xl border px-3 py-1.5 text-xs font-medium transition-colors ${
              stat === o.key
                ? "border-slate-600 bg-slate-800 text-slate-100"
                : "border-slate-800 text-slate-400 hover:text-slate-200"
            }`}
          >
            {o.label}
          </button>
        ))}
      </div>
      {statOption.note && <p className="text-xs text-amber-300/80">{statOption.note}</p>}

      <div className="rounded-3xl border border-slate-800 bg-slate-900/30 p-5">
        <label className="text-xs font-medium uppercase tracking-wide text-slate-500" htmlFor="rp-search">
          {GROUP_LABELS[group]}
        </label>
        <input
          id="rp-search"
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by name"
          className="mt-2 w-full rounded-xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-slate-100 outline-none focus:border-slate-600"
        />
        {playersQuery.isLoading && <p className="mt-3 text-sm text-slate-500">Loading players…</p>}
        {matches.length > 0 && (
          <ul className="mt-3 flex flex-wrap gap-2">
            {matches.map((r) => (
              <li key={r.gsis_id}>
                <button
                  type="button"
                  onClick={() => {
                    setSelected(r.gsis_id);
                    setQuery("");
                  }}
                  className="rounded-xl border border-slate-800 px-3 py-1.5 text-xs text-slate-300 transition-colors hover:border-slate-600 hover:text-slate-100"
                >
                  {r.name} <span className="text-slate-500">{r.position}</span>{" "}
                  <span className="text-slate-600">{r.team}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {selected == null && <p className="text-sm text-slate-500">Search for a player to get started.</p>}

      {selected != null && propQuery.isLoading && <p className="text-sm text-slate-500">Loading…</p>}

      {selected != null && propQuery.isError && (
        <div className="rounded-2xl border border-red-900/40 bg-red-950/20 px-4 py-3 text-sm text-red-300">
          No projection available for this player and stat this week (bye, no history, or no game).
        </div>
      )}

      {prop && (
        <div className="space-y-5 rounded-3xl border border-slate-800 p-5">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <div>
              <h2 className="text-xl font-semibold">
                {prop.name}
                {prop.position && <span className="ml-2 text-base text-slate-500">{prop.position}</span>}
              </h2>
              <p className="text-sm text-slate-500">
                {prop.team} vs {prop.opponent} · Week {prop.week}
              </p>
            </div>
            <p className="text-sm text-slate-400">
              Projected{" "}
              <span className="font-semibold text-slate-100">
                {prop.mean.toFixed(meanDigits)} {unit}
              </span>
            </p>
          </div>

          {prop.thin_sample && (
            <p className="rounded-xl border border-amber-900/40 bg-amber-950/20 px-3 py-2 text-xs text-amber-300">
              Only {prop.games_used} prior games. The estimate is less reliable until more games are in.
            </p>
          )}

          <div>
            <div className="flex flex-wrap items-baseline justify-between gap-3">
              <p className="text-sm text-slate-400">{statLabel} line</p>
              <p className="text-3xl font-bold tabular-nums">
                {shownLine} {unit}
              </p>
            </div>
            <input
              type="range"
              min={0}
              max={prop.line_max}
              step={1}
              value={shownLine}
              onChange={(e) => setLine(Number(e.target.value))}
              aria-label={`${statLabel} line`}
              className="mt-3 w-full accent-sky-400"
            />
            <div className="mt-1 flex justify-between text-[11px] text-slate-600">
              <span>0</span>
              <span>{prop.line_max}</span>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">
                Over (≥ {shownLine} {unit})
              </p>
              <p className="mt-1 text-2xl font-semibold tabular-nums text-emerald-400">
                {pOver != null ? pct(pOver) : "—"}
              </p>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">
                Under (&lt; {shownLine} {unit})
              </p>
              <p className="mt-1 text-2xl font-semibold tabular-nums text-rose-400">
                {pOver != null ? pct(1 - pOver) : "—"}
              </p>
            </div>
          </div>

          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">Recent games</p>
            <div className="overflow-x-auto rounded-2xl border border-slate-800">
              <table className="w-full border-collapse text-sm">
                <thead className="bg-slate-900/60 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-3 py-2 text-left font-semibold">Week</th>
                    <th className="px-3 py-2 text-left font-semibold">Opp</th>
                    {GAME_LOG_COLUMNS[group].map((c) => (
                      <th key={c.key} className="px-3 py-2 text-right font-semibold">
                        {c.label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {prop.game_log.map((g) => (
                    <tr key={`${g.season}-${g.week}`} className="border-t border-slate-800/60">
                      <td className="px-3 py-2 text-slate-400">
                        {g.season} W{g.week}
                      </td>
                      <td className="px-3 py-2 text-slate-300">{g.opponent}</td>
                      {GAME_LOG_COLUMNS[group].map((c) => (
                        <td key={c.key} className="px-3 py-2 text-right tabular-nums text-slate-300">
                          {g.values[c.key]}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">{prop.opponent} defense</p>
              <p className="mt-2 text-sm text-slate-300">
                Allows{" "}
                <span className="font-semibold text-slate-100">
                  {prop.context.opponent.avg_season ?? "—"}
                </span>{" "}
                {unit} per {GROUP_NOUN[group]} game (league{" "}
                {prop.context.opponent.league_avg ?? "—"})
              </p>
              <p className="mt-1 text-xs text-slate-500">
                Last 4 games: {prop.context.opponent.avg_last4 ?? "—"} {unit}
              </p>
              {prop.context.opponent.top_games.length > 0 && (
                <div className="mt-3">
                  <p className="text-[11px] uppercase tracking-wide text-slate-600">
                    Most {statLabel.toLowerCase()} allowed
                  </p>
                  <ul className="mt-1 space-y-1 text-xs text-slate-400">
                    {prop.context.opponent.top_games.map((t) => (
                      <li key={`${t.season}-${t.week}-${t.player}`}>
                        {t.player} · {t.value} {unit} · {t.season} W{t.week}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">Role</p>
              <dl className="mt-2 space-y-2 text-sm">
                <div className="flex justify-between gap-3">
                  <dt className="text-slate-400">{VOLUME_LABEL[group]} per game</dt>
                  <dd className="tabular-nums text-slate-100">
                    {fmtOrDash(prop.context.usage.volume_per_game_season, 1)}
                    <span className="ml-1 text-xs text-slate-500">
                      (last 4 {fmtOrDash(prop.context.usage.volume_per_game_last4, 1)})
                    </span>
                  </dd>
                </div>
                {prop.context.usage.target_share_season != null && (
                  <div className="flex justify-between gap-3">
                    <dt className="text-slate-400">Target share</dt>
                    <dd className="tabular-nums text-slate-100">
                      {pct(prop.context.usage.target_share_season)}
                      <span className="ml-1 text-xs text-slate-500">
                        (last 4 {fmtOrDash(prop.context.usage.target_share_last4, 1, true)})
                      </span>
                    </dd>
                  </div>
                )}
                {prop.context.usage.carry_share_season != null && (
                  <div className="flex justify-between gap-3">
                    <dt className="text-slate-400">Carry share</dt>
                    <dd className="tabular-nums text-slate-100">
                      {pct(prop.context.usage.carry_share_season)}
                      <span className="ml-1 text-xs text-slate-500">
                        (last 4 {fmtOrDash(prop.context.usage.carry_share_last4, 1, true)})
                      </span>
                    </dd>
                  </div>
                )}
                {prop.context.usage.air_yards_share_season != null && (
                  <div className="flex justify-between gap-3">
                    <dt className="text-slate-400">Air yards share</dt>
                    <dd className="tabular-nums text-slate-100">{pct(prop.context.usage.air_yards_share_season)}</dd>
                  </div>
                )}
              </dl>
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">Game</p>
              <p className="mt-2 text-sm text-slate-300">
                Total{" "}
                <span className="font-semibold text-slate-100">{prop.context.game.total_line ?? "—"}</span>
              </p>
              <p className="mt-1 text-sm text-slate-300">
                {prop.team} implied total{" "}
                <span className="font-semibold text-slate-100">
                  {prop.context.game.implied_team_total ?? "—"}
                </span>
              </p>
              <p className="mt-1 text-xs text-slate-500">Roof: {prop.context.game.roof ?? "—"}</p>
            </div>
          </div>

          <p className="text-xs leading-relaxed text-slate-600">{prop.disclaimer}</p>
        </div>
      )}

      {calibration && calibration.brier_model != null && calibration.brier_baseline != null && (
        <div className="rounded-3xl border border-slate-800 bg-slate-900/30 p-5">
          <button
            type="button"
            onClick={() => setShowCalibration((v) => !v)}
            aria-expanded={showCalibration}
            className="flex w-full items-center justify-between gap-3 text-left"
          >
            <span>
              <span className="block text-base font-semibold">Model Accuracy · {statLabel}</span>
              <span className="mt-1 block text-sm text-slate-400">
                Backtested on {calibration.first_season}–{calibration.last_season}. Click to{" "}
                {showCalibration ? "hide" : "show"} details.
              </span>
            </span>
            <span aria-hidden className="text-xs text-slate-500">
              {showCalibration ? "▲" : "▼"}
            </span>
          </button>
        </div>
      )}

      {showCalibration && calibration && calibration.brier_model != null && calibration.brier_baseline != null && (
        <div className="space-y-4 rounded-3xl border border-slate-800 bg-slate-900/30 p-5">
          <p className="text-sm text-slate-400">
            Backtested on {calibration.first_season}–{calibration.last_season} using only the data available
            before each game. Lower Brier score is better.
          </p>

          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">This model</p>
              <p className="mt-1 text-xl font-semibold tabular-nums">{calibration.brier_model.toFixed(4)}</p>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">Naive baseline</p>
              <p className="mt-1 text-xl font-semibold tabular-nums text-slate-400">
                {calibration.brier_baseline.toFixed(4)}
              </p>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">Predictions scored</p>
              <p className="mt-1 text-xl font-semibold tabular-nums">{calibration.predictions.toLocaleString()}</p>
            </div>
          </div>

          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">
              Predicted vs. actual hit rate
            </p>
            <div className="overflow-x-auto rounded-2xl border border-slate-800">
              <table className="w-full border-collapse text-sm">
                <thead className="bg-slate-900/60 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-3 py-2 text-left font-semibold">Predicted</th>
                    <th className="px-3 py-2 text-right font-semibold">Actual</th>
                    <th className="px-3 py-2 text-right font-semibold">Predictions</th>
                  </tr>
                </thead>
                <tbody>
                  {calibration.buckets.map((b) => (
                    <tr key={b.predicted} className="border-t border-slate-800/60">
                      <td className="px-3 py-2 tabular-nums text-slate-300">{pct(b.predicted)}</td>
                      <td className="px-3 py-2 text-right tabular-nums text-slate-100">{pct(b.actual)}</td>
                      <td className="px-3 py-2 text-right tabular-nums text-slate-500">{b.n.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-2 text-xs leading-relaxed text-slate-600">
              When the model says an outcome is likely, it should happen about that often. Rows where
              predicted and actual are close mean the probabilities can be trusted.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
