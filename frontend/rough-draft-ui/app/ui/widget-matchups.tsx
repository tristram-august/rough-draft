import { formatGameDay, formatKickoffTime, spreadLabel, type UpcomingSchedule } from "../lib/dashboard";

export function MatchupsWidget({ schedule }: { schedule: UpcomingSchedule }) {
  if (schedule.games.length === 0) return null;

  const { week, days_until_kickoff: days, in_season, game_type } = schedule;
  const isPlayoffs = game_type != null && game_type !== "REG";
  const weekLabel = isPlayoffs ? game_type : week != null ? `Week ${week}` : "Next up";

  return (
    <section className="rounded-3xl border border-slate-800 bg-slate-900/30 p-5 sm:p-6">
      <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-sm font-semibold uppercase tracking-[0.14em] text-slate-400">
          {in_season ? "This week" : "Next up"} · {weekLabel}
        </h2>
        {days != null && (
          <span className="text-xs font-medium text-sky-400">
            {days <= 0
              ? "Kickoff today"
              : days === 1
                ? "Kicks off tomorrow"
                : `${days} days to kickoff`}
          </span>
        )}
      </div>

      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {schedule.games.map((g) => {
          const spread = spreadLabel(g);
          return (
            <div
              key={g.game_id}
              className="rounded-2xl border border-slate-800/80 bg-slate-950/40 px-3.5 py-3"
            >
              <div className="flex items-center justify-between text-[11px] text-slate-500">
                <span>
                  {g.weekday?.slice(0, 3)} {formatGameDay(g.gameday)} ·{" "}
                  {formatKickoffTime(g.gametime)}
                </span>
                {g.div_game && (
                  <span className="rounded-full border border-slate-800 px-1.5 text-[10px] text-slate-500">
                    DIV
                  </span>
                )}
              </div>

              <div className="mt-1.5 flex items-baseline justify-between gap-2">
                <span className="truncate text-sm font-medium text-slate-200">
                  {g.away_name ?? g.away_team}
                  <span className="mx-1.5 text-slate-600">@</span>
                  {g.home_name ?? g.home_team}
                </span>
                {g.final && (
                  <span className="shrink-0 text-sm font-semibold tabular-nums text-slate-100">
                    {g.away_score}–{g.home_score}
                  </span>
                )}
              </div>

              {!g.final && (spread || g.total_line != null) && (
                <div className="mt-1 flex gap-3 text-[11px] text-slate-600 tabular-nums">
                  {spread && <span>{spread}</span>}
                  {g.total_line != null && <span>O/U {g.total_line}</span>}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
