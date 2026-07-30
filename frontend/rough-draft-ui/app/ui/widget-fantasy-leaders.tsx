import Link from "next/link";
import type { FantasyLeaderRow } from "../lib/fantasy";

const POSITION_COLORS: Record<string, string> = {
  QB: "text-rose-400",
  RB: "text-emerald-400",
  WR: "text-sky-400",
  TE: "text-amber-400",
};

export function FantasyLeadersWidget({
  rows,
  season,
}: {
  rows: FantasyLeaderRow[];
  season: number;
}) {
  if (rows.length === 0) return null;

  return (
    <section className="rounded-3xl border border-slate-800 bg-slate-900/30 p-5">
      <div className="mb-3 flex items-baseline justify-between gap-2">
        <h2 className="text-sm font-semibold uppercase tracking-[0.14em] text-slate-400">
          Fantasy leaders
        </h2>
        <span className="text-[11px] text-slate-600">{season} PPR</span>
      </div>

      <ol className="space-y-1.5">
        {rows.map((row) => (
          <li key={row.gsis_id}>
            <Link
              href={`/fantasy/player/${row.gsis_id}?season=${season}&scoring=ppr`}
              className="flex items-baseline gap-2 rounded-lg px-1.5 py-1 transition-colors hover:bg-slate-900/60"
            >
              <span className="w-4 shrink-0 text-[11px] text-slate-600 tabular-nums">
                {row.rank}
              </span>
              <span className="min-w-0 flex-1 truncate text-sm text-slate-200">{row.name}</span>
              {row.position && (
                <span
                  className={`shrink-0 text-[11px] font-semibold ${
                    POSITION_COLORS[row.position] ?? "text-slate-500"
                  }`}
                >
                  {row.position}
                </span>
              )}
              <span className="shrink-0 text-sm font-semibold text-slate-100 tabular-nums">
                {row.fantasy_points.toFixed(0)}
              </span>
            </Link>
          </li>
        ))}
      </ol>

      <Link
        href="/fantasy"
        className="mt-3 block text-xs font-medium text-sky-400 transition-colors hover:text-sky-300"
      >
        Full rankings <span aria-hidden>→</span>
      </Link>
    </section>
  );
}
