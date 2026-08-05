"use client";

import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "./page-header";
import { Segmented } from "./segmented";
import { useAuth } from "../contexts/auth-context";
import { formatGameDay, formatKickoffTime, spreadLabel } from "../lib/dashboard";
import { teamColor } from "../lib/team-colors";
import { MatchupStatsButton } from "./matchup-stats-button";
import {
  fetchPickLeaderboard,
  fetchPredictionAccuracy,
  fetchSlate,
  submitPick,
  type SlateGame,
} from "../lib/picks";

function TeamButton({
  abbrev,
  name,
  score,
  picked,
  locked,
  isWinner,
  sharePct,
  onPick,
}: {
  abbrev: string;
  name: string | null;
  score: number | null;
  picked: boolean;
  locked: boolean;
  isWinner: boolean | null;
  sharePct: number | null;
  onPick: () => void;
}) {
  const color = teamColor(abbrev);
  const isFinalLoser = locked && isWinner === false;

  // Team color always tints the button; how strongly depends on state. A
  // locked loser dims toward neutral, a locked winner and an active pick
  // both read as "the strong choice" — the PICK badge still disambiguates
  // "I chose this" from "this team won" regardless of color.
  let bgAlpha = "26"; // ~15%, resting
  let borderAlpha = "59"; // ~35%, resting
  if (picked) {
    bgAlpha = "66"; // ~40%
    borderAlpha = "FF";
  } else if (isFinalLoser) {
    bgAlpha = "14"; // ~8%
    borderAlpha = "26"; // ~15%
  } else if (locked && isWinner) {
    bgAlpha = "40"; // ~25%
    borderAlpha = "B3"; // ~70%
  }

  return (
    <button
      type="button"
      onClick={onPick}
      disabled={locked}
      className={`relative flex-1 overflow-hidden rounded-xl border px-3 py-2.5 text-left transition-[filter] ${
        locked ? "" : "hover:brightness-125"
      }`}
      style={{ backgroundColor: `${color}${bgAlpha}`, borderColor: `${color}${borderAlpha}` }}
    >
      {/* Community share fills the button behind the label — kept neutral
          so it stays legible against every team's background tint. */}
      {sharePct != null && sharePct > 0 && (
        <span
          aria-hidden
          className="absolute inset-y-0 left-0 bg-slate-950/35"
          style={{ width: `${sharePct}%` }}
        />
      )}
      <span className="relative flex items-center justify-between gap-2">
        <span className="min-w-0">
          <span
            className={`block truncate text-sm font-medium ${
              isFinalLoser ? "text-slate-400" : "text-slate-100"
            }`}
          >
            {name ?? abbrev}
          </span>
          {sharePct != null && (
            <span className="text-[10px] text-slate-400">{Math.round(sharePct)}% picked</span>
          )}
        </span>
        <span className="flex shrink-0 items-center gap-1.5">
          {score != null && (
            <span
              className={`text-sm font-semibold tabular-nums ${
                isWinner ? "text-slate-100" : "text-slate-400"
              }`}
            >
              {score}
            </span>
          )}
          {picked && <span className="text-[10px] font-semibold text-sky-400">PICK</span>}
        </span>
      </span>
    </button>
  );
}

function GameRow({
  game,
  onPick,
  pending,
}: {
  game: SlateGame;
  onPick: (team: string) => void;
  pending: boolean;
}) {
  const total = game.split.total;
  const awayPct = total > 0 ? (game.split.away / total) * 100 : null;
  const homePct = total > 0 ? (game.split.home / total) * 100 : null;
  const spread = spreadLabel(game);

  const modelPct =
    game.model_favorite && game.model_home_win_prob != null
      ? Math.round(
          (game.model_favorite === game.home_team
            ? game.model_home_win_prob
            : 1 - game.model_home_win_prob) * 100
        )
      : null;

  const resultBadge =
    game.your_result === "win"
      ? { label: "WON", cls: "border-emerald-800/60 bg-emerald-950/30 text-emerald-400" }
      : game.your_result === "loss"
        ? { label: "LOST", cls: "border-rose-900/60 bg-rose-950/30 text-rose-400" }
        : game.your_result === "push"
          ? { label: "PUSH", cls: "border-slate-700 bg-slate-900 text-slate-400" }
          : null;

  return (
    <div
      className={`rounded-2xl border border-slate-800 bg-slate-900/30 p-3.5 transition-opacity ${
        pending ? "opacity-60" : ""
      }`}
    >
      <div className="mb-2 flex flex-wrap items-center justify-between gap-x-2 gap-y-1 text-[11px] text-slate-500">
        <span>
          {game.weekday?.slice(0, 3)} {formatGameDay(game.gameday)} ·{" "}
          {formatKickoffTime(game.gametime)}
          {game.div_game ? " · DIV" : ""}
        </span>
        <span className="flex items-center gap-2">
          {!game.final && (spread || game.total_line != null) && (
            <span className="tabular-nums text-slate-600">
              {spread}
              {spread && game.total_line != null ? " · " : ""}
              {game.total_line != null ? `O/U ${game.total_line}` : ""}
            </span>
          )}
          {modelPct != null && (
            <span className="tabular-nums text-slate-600" title="Elo model's win probability">
              Model {game.model_favorite} {modelPct}%
            </span>
          )}
          {resultBadge && (
            <span className={`rounded-full border px-1.5 py-0.5 font-semibold ${resultBadge.cls}`}>
              {resultBadge.label}
            </span>
          )}
          {game.final ? (
            <span className="text-slate-600">Final</span>
          ) : game.locked ? (
            <span className="text-amber-500/80">Locked</span>
          ) : null}
        </span>
      </div>

      <div className="flex gap-2">
        <TeamButton
          abbrev={game.away_team}
          name={game.away_name}
          score={game.away_score}
          picked={game.your_pick === game.away_team}
          locked={game.locked}
          isWinner={game.winner ? game.winner === game.away_team : null}
          sharePct={awayPct}
          onPick={() => onPick(game.away_team)}
        />
        <TeamButton
          abbrev={game.home_team}
          name={game.home_name}
          score={game.home_score}
          picked={game.your_pick === game.home_team}
          locked={game.locked}
          isWinner={game.winner ? game.winner === game.home_team : null}
          sharePct={homePct}
          onPick={() => onPick(game.home_team)}
        />
      </div>

      <div className="mt-2 flex justify-center">
        <MatchupStatsButton
          gameId={game.game_id}
          awayTeam={game.away_team}
          homeTeam={game.home_team}
          awayName={game.away_name}
          homeName={game.home_name}
        />
      </div>
    </div>
  );
}

function StandingsPanel({
  season,
  week,
  token,
}: {
  season: number;
  week: number | null;
  token: string | null;
}) {
  const [scope, setScope] = React.useState<"week" | "season">("week");

  const { data, isLoading } = useQuery({
    queryKey: ["pick-leaderboard", season, scope === "week" ? week : null, token],
    queryFn: () => fetchPickLeaderboard(season, scope === "week" ? week : null, token),
  });

  const rows = data?.rows ?? [];

  return (
    <section className="rounded-3xl border border-slate-800 bg-slate-900/30 p-5">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold uppercase tracking-[0.14em] text-slate-400">
          Standings
        </h2>
        <Segmented
          ariaLabel="Standings scope"
          value={scope}
          onChange={setScope}
          options={[
            { value: "week", label: "Week" },
            { value: "season", label: "Season" },
          ]}
        />
      </div>

      {isLoading && <p className="text-sm text-slate-500">Loading…</p>}

      {data && rows.length === 0 && (
        <p className="text-sm text-slate-500">
          No graded picks yet. Standings fill in as games go final.
        </p>
      )}

      {rows.length > 0 && (
        <ol className="space-y-1">
          {rows.map((row) => (
            <li
              key={`${row.voter_type}-${row.display_name}-${row.rank}`}
              className={`flex items-baseline gap-2 rounded-lg px-1.5 py-1 ${
                row.is_you ? "bg-sky-950/30" : ""
              }`}
            >
              <span className="w-4 shrink-0 text-[11px] text-slate-600 tabular-nums">
                {row.rank}
              </span>
              <span
                className={`min-w-0 flex-1 truncate text-sm ${
                  row.is_you ? "font-medium text-sky-300" : "text-slate-300"
                }`}
              >
                {row.display_name}
                {row.is_you && <span className="ml-1.5 text-[10px] text-sky-500">you</span>}
              </span>
              <span className="shrink-0 text-sm text-slate-400 tabular-nums">
                {row.wins}-{row.losses}
                {row.pushes > 0 ? `-${row.pushes}` : ""}
              </span>
              <span className="w-10 shrink-0 text-right text-xs text-slate-600 tabular-nums">
                {row.pct.toFixed(3).replace(/^0/, "")}
              </span>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

function AccuracyBar({ label, pct }: { label: string; pct: number }) {
  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between text-xs">
        <span className="text-slate-400">{label}</span>
        <span className="tabular-nums text-slate-300">{pct.toFixed(1)}%</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full border border-slate-800 bg-slate-950/50">
        <div className="h-full bg-slate-200/70" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function ModelAccuracyPanel() {
  const { data } = useQuery({
    queryKey: ["prediction-accuracy"],
    queryFn: fetchPredictionAccuracy,
  });

  if (!data || data.model_graded === 0) return null;

  const modelPct = (data.model_correct / data.model_graded) * 100;
  const vegasPct = data.vegas_graded > 0 ? (data.vegas_correct / data.vegas_graded) * 100 : null;

  return (
    <section className="rounded-3xl border border-slate-800 bg-slate-900/30 p-5">
      <h2 className="mb-1 text-sm font-semibold uppercase tracking-[0.14em] text-slate-400">
        Elo model
      </h2>
      <p className="mb-3 text-[11px] leading-relaxed text-slate-600">
        Straight-up picks, {data.season_from}–{data.season_to}. Out-of-sample: this range never
        influenced the model&apos;s constants, so it&apos;s a genuine backtest, not a number fit to
        itself.
      </p>
      <div className="space-y-3">
        <AccuracyBar label="Model" pct={modelPct} />
        {vegasPct != null && <AccuracyBar label="Vegas favorite" pct={vegasPct} />}
      </div>
    </section>
  );
}

export default function PicksPage() {
  const { user, token } = useAuth();
  const queryClient = useQueryClient();
  const [error, setError] = React.useState<string | null>(null);
  const [pendingGame, setPendingGame] = React.useState<string | null>(null);

  const slateQuery = useQuery({
    queryKey: ["picks-slate", token],
    queryFn: () => fetchSlate({ token }),
  });

  const slate = slateQuery.data;
  const games = slate?.games ?? [];

  const mutation = useMutation({
    mutationFn: ({ gameId, team }: { gameId: string; team: string }) =>
      submitPick(gameId, team, token),
    onMutate: ({ gameId }) => {
      setError(null);
      setPendingGame(gameId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["picks-slate"] });
      queryClient.invalidateQueries({ queryKey: ["pick-leaderboard"] });
    },
    onError: (err: Error) => setError(err.message),
    onSettled: () => setPendingGame(null),
  });

  const madeCount = games.filter((g) => g.your_pick).length;

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <PageHeader
        eyebrow="Picks"
        title={slate?.week != null ? `Week ${slate.week} picks` : "Game picks"}
        subtitle="Pick every game straight up. Picks lock at kickoff and grade themselves as scores come in."
      />

      {error && (
        <div className="mb-4 rounded-xl border border-red-800/40 bg-red-950/20 px-3 py-2 text-sm text-red-300">
          {error}
        </div>
      )}

      {!user && (
        <p className="mb-4 text-xs text-slate-500">
          Picking as a guest — sign in to keep your record across devices.
        </p>
      )}

      {slateQuery.isLoading && <p className="text-sm text-slate-500">Loading…</p>}
      {slateQuery.isError && (
        <div className="rounded-2xl border border-red-900/40 bg-red-950/20 px-4 py-3 text-sm text-red-300">
          Couldn&apos;t load the slate. Try again in a moment.
        </div>
      )}

      {games.length > 0 && (
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <p className="mb-3 text-xs text-slate-500">
              {madeCount} of {games.length} picked
            </p>
            <div className="space-y-2.5">
              {games.map((game) => (
                <GameRow
                  key={game.game_id}
                  game={game}
                  pending={pendingGame === game.game_id}
                  onPick={(team) => mutation.mutate({ gameId: game.game_id, team })}
                />
              ))}
            </div>
          </div>

          <div className="space-y-6">
            {slate?.season != null && (
              <StandingsPanel season={slate.season} week={slate.week} token={token} />
            )}
            <ModelAccuracyPanel />
          </div>
        </div>
      )}

      {slate && games.length === 0 && (
        <p className="text-sm text-slate-500">No games scheduled.</p>
      )}
    </div>
  );
}
