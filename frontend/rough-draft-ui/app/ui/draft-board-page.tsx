// frontend/rough-draft-ui/app/ui/draft-board-page.tsx
"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";

/** -----------------------------
 * Types (minimal, UI-focused)
 * ------------------------------ */

type CommunityVotesOut = {
  success: number;
  bust: number;
  total: number;
  community_score: number;
  community_label: string;
};

type DraftBoardRow = {
  year: number;
  round: number;
  pick_in_round: number;
  overall: number;
  team: { abbrev: string; city: string; name: string };
  player: { full_name: string; position: string; college?: string | null; gsis_id?: string | null };
  outcome?: { label: string } | null;
  community_votes?: CommunityVotesOut | null;
  your_vote?: { value: "success" | "bust" } | null;
};

type PickDetail = {
  id: number;
  year: number;
  round: number;
  pick_in_round: number;
  overall: number;
  team: { abbrev: string; city: string; name: string };
  player: { full_name: string; position: string; college?: string | null; gsis_id?: string | null };
  community_votes?: CommunityVotesOut | null;
  your_vote?: { value: "success" | "bust" } | null;
};

type DrawerTotals = {
  games: number;
  passing: { att: number; cmp: number; yds: number; td: number; int: number; epa: number; cpoe_avg: number | null };
  rushing: { att: number; yds: number; td: number; epa: number };
  receiving: {
    targets: number;
    rec: number;
    yds: number;
    td: number;
    epa: number;
    target_share_avg: number | null;
    air_yards: number;
    air_yards_share_avg: number | null;
  };
  defense: { tackles: number; sacks: number; int: number; ff: number; fr: number; td: number };
  ball_security: { fumbles_lost: number };
};

type DrawerNotable = { headline: string } & Record<string, any>;

type DrawerTab = {
  scope: "career" | "draft_team" | "other_teams";
  title: string;
  team_filter: null | { equals?: string; not_equals?: string };
  totals: DrawerTotals;
  notables: { best_season: DrawerNotable | null; best_game: DrawerNotable | null };
  meta: {
    games_distinct: number;
    row_count: number;
    seasons_in_scope: number[];
    teams_in_scope: string[];
    teams_in_scope_by_games: Array<{ team: string; games: number }>;
  };
};

type DrawerResponse = {
  player: {
    gsis_id: string;
    display_name: string | null;
    position: string | null;
    position_group: string | null;
    birth_date: string | null;
    height: number | null;
    weight: number | null;
    headshot: string | null;
    college_name: string | null;
    latest_team: string | null;
    status: string | null;
    years_of_experience: number | null;
  };
  draft_context: { draft_team: string };
  tabs: {
    career: DrawerTab;
    draft_team: DrawerTab;
    other_teams: DrawerTab;
  };
  ui_hints: { default_tab: "career" | "draft_team" | "other_teams" };
};

type RankingsItem = {
  team?: string;
  player?: string;
  draft_team?: string | null;
  success: number;
  bust: number;
  totalVotes: number;
  ratio: number | null;
};

/** -----------------------------
 * Constants / helpers
 * ------------------------------ */

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

function getClientId(): string {
  const key = "rough_draft_client_id";
  const existing = typeof window !== "undefined" ? window.localStorage.getItem(key) : null;
  if (existing) return existing;
  const id = crypto.randomUUID();
  window.localStorage.setItem(key, id);
  return id;
}

function posVariant(pos: string): "qb" | "rb" | "wr" | "te" | "def" | "k" | "other" {
  const p = (pos || "").toUpperCase();
  if (p === "QB") return "qb";
  if (p === "RB") return "rb";
  if (p === "WR") return "wr";
  if (p === "TE") return "te";
  if (["CB", "S", "DB", "LB", "DL", "EDGE", "DE", "DT"].includes(p)) return "def";
  if (["K", "P"].includes(p)) return "k";
  return "other";
}

function Pill({ children, variant }: { children: React.ReactNode; variant: ReturnType<typeof posVariant> }) {
  const base = "inline-flex items-center rounded-full border px-2 py-0.5 text-xs";
  const map: Record<string, string> = {
    qb: "border-blue-700/50 bg-blue-950/40 text-blue-200",
    rb: "border-emerald-700/50 bg-emerald-950/40 text-emerald-200",
    wr: "border-fuchsia-700/50 bg-fuchsia-950/40 text-fuchsia-200",
    te: "border-purple-700/50 bg-purple-950/40 text-purple-200",
    def: "border-amber-700/50 bg-amber-950/40 text-amber-200",
    k: "border-slate-700 bg-slate-950 text-slate-200",
    other: "border-slate-700 bg-slate-950 text-slate-200",
  };
  return <span className={`${base} ${map[variant] ?? map.other}`}>{children}</span>;
}

function ScoreBadge({ cv }: { cv: CommunityVotesOut | null }) {
  const total = cv?.total ?? 0;
  const score = cv?.community_score ?? 0;
  const label = total === 0 ? "No votes" : `${score}%`;
  return (
    <div className="inline-flex items-center gap-2 rounded-2xl border border-slate-800 bg-slate-950/40 px-3 py-1">
      <span className="text-xs text-slate-300">{label}</span>
      <span className="text-[10px] text-slate-500">({total})</span>
    </div>
  );
}

function VoteBar({ cv }: { cv: CommunityVotesOut | null }) {
  const success = cv?.success ?? 0;
  const bust = cv?.bust ?? 0;
  const total = success + bust;
  const pct = total > 0 ? Math.round((success / total) * 100) : 0;
  return (
    <div className="mt-2 h-2 w-full overflow-hidden rounded-full border border-slate-800 bg-slate-950/50">
      <div className="h-full bg-slate-200/70" style={{ width: `${pct}%` }} />
    </div>
  );
}

function Drawer({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <>
      <div
        className={`fixed inset-0 bg-black/50 transition-opacity ${open ? "opacity-100" : "opacity-0 pointer-events-none"}`}
        onClick={onClose}
      />
      <aside
        className={`fixed top-0 right-0 h-full w-full max-w-xl border-l border-slate-800 bg-slate-950 text-slate-100 shadow-2xl transition-transform ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <div className="p-4 border-b border-slate-800 flex items-start justify-between gap-3">
          <div>
            <div className="text-xs text-slate-500">Pick Detail</div>
            <div className="text-lg font-semibold leading-tight text-slate-100">{title}</div>
          </div>
          <button
            className="rounded-lg border border-slate-800 bg-slate-900/40 px-3 py-1.5 text-sm hover:bg-slate-800/60"
            onClick={onClose}
            type="button"
          >
            Close
          </button>
        </div>
        <div className="p-4 overflow-auto h-[calc(100%-65px)]">{children}</div>
      </aside>
    </>
  );
}

/** -----------------------------
 * API calls
 * ------------------------------ */

async function fetchDraftBoard(args: {
  year: number;
  round?: number | null;
  team?: string;
  pos?: string;
  q?: string;
  limit: number;
  offset: number;
}): Promise<DraftBoardRow[]> {
  const url = new URL(`${API_BASE}/draft`);
  url.searchParams.set("year", String(args.year));
  if (args.round) url.searchParams.set("round", String(args.round));
  if (args.team) url.searchParams.set("team", args.team);
  if (args.pos) url.searchParams.set("pos", args.pos);
  if (args.q) url.searchParams.set("q", args.q);
  url.searchParams.set("limit", String(args.limit));
  url.searchParams.set("offset", String(args.offset));

  const res = await fetch(url.toString(), {
    headers: { "X-Client-Id": getClientId() },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Draft fetch failed: ${res.status}`);
  return res.json();
}

async function fetchPickDetail(year: number, overall: number): Promise<PickDetail> {
  const res = await fetch(`${API_BASE}/pick/${year}/${overall}`, {
    headers: { "X-Client-Id": getClientId() },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Pick fetch failed: ${res.status}`);
  return res.json();
}

async function postVote(year: number, overall: number, value: "success" | "bust"): Promise<CommunityVotesOut> {
  const res = await fetch(`${API_BASE}/pick/${year}/${overall}/vote`, {
    method: "POST",
    headers: {
      "X-Client-Id": getClientId(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ value }),
  });
  if (!res.ok) throw new Error(`Vote failed: ${res.status}`);
  return res.json();
}

async function fetchDrawer(gsisId: string, draftTeam: string): Promise<DrawerResponse> {
  const url = new URL(`${API_BASE}/player/${gsisId}/drawer`);
  url.searchParams.set("draft_team", draftTeam);

  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) throw new Error(`Drawer fetch failed: ${res.status}`);
  return res.json();
}

async function fetchRankings(
  year: number,
  groupBy: "team" | "player",
  sort: "best" | "worst" = "best",
  minVotes: number = 1,
  limit: number = 32,
): Promise<{ items: RankingsItem[] }> {
  const url = new URL(`${API_BASE}/rankings`);
  url.searchParams.set("year", String(year));
  url.searchParams.set("groupBy", groupBy);
  url.searchParams.set("sort", sort);
  url.searchParams.set("minVotes", String(minVotes));
  url.searchParams.set("limit", String(limit));
  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) throw new Error(`Rankings fetch failed: ${res.status}`);
  return res.json();
}

/** -----------------------------
 * UI
 * ------------------------------ */


function MiniVoteButtons({
  yourVote,
  disabled,
  onVote,
}: {
  yourVote: DraftBoardRow["your_vote"];
  disabled: boolean;
  onVote: (value: "bust" | "success") => void;
}) {
  const active = yourVote?.value ?? null;

  const base =
    "inline-flex h-7 w-7 items-center justify-center rounded-xl border text-xs leading-none transition-colors disabled:opacity-50";
  const inactive = "border-slate-800 bg-slate-950/20 text-slate-200 hover:bg-slate-900/40";
  const activeCls = "border-slate-200/30 bg-slate-200/10 text-slate-100";

  return (
    <div
      className="flex items-center gap-1"
      onClick={(e) => e.stopPropagation()}
      onMouseDown={(e) => e.stopPropagation()}
    >
      <button
        type="button"
        aria-label="Vote bust"
        disabled={disabled}
        className={`${base} ${active === "bust" ? activeCls : inactive}`}
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          onVote("bust");
        }}
        title="Bust"
      >
        ❌
      </button>
      <button
        type="button"
        aria-label="Vote success"
        disabled={disabled}
        className={`${base} ${active === "success" ? activeCls : inactive}`}
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          onVote("success");
        }}
        title="Success"
      >
        ✅
      </button>
    </div>
  );
}

function Row({
  row,
  onOpen,
  onVote,
  isVoting,
}: {
  row: DraftBoardRow;
  onOpen: () => void;
  onVote: (value: "success" | "bust") => void;
  isVoting: boolean;
}) {
  const cv = row.community_votes ?? null;

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/30 hover:bg-slate-900/50 transition-colors px-4 py-3">
      <div className="flex items-center gap-4">
        {/* Main click target (opens drawer) */}
        <button
          type="button"
          onClick={onOpen}
          className="flex min-w-0 flex-1 items-center gap-4 text-left"
          aria-label={`Open pick #${row.overall} details`}
        >
          <div className="w-16 shrink-0">
            <div className="font-mono text-sm text-slate-200">#{row.overall}</div>
            <div className="text-[11px] text-slate-500">
              R{row.round}P{row.pick_in_round}
            </div>
          </div>

          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 min-w-0">
              <div className="font-semibold text-slate-100 truncate">{row.player.full_name}</div>
              <Pill variant={posVariant(row.player.position)}>{row.player.position}</Pill>
              {row.player.college ? (
                <span className="text-xs text-slate-400 truncate">{row.player.college}</span>
              ) : null}
            </div>
            <div className="mt-1 text-xs text-slate-500">
              <span className="text-slate-300">{row.team.abbrev}</span> — {row.team.city} {row.team.name}
              {row.outcome ? <span className="text-slate-500"> • Model: {row.outcome.label}</span> : null}
            </div>
          </div>
        </button>

        {/* Right column: score + mini buttons + bar */}
        <div className="w-44 shrink-0">
          <div className="flex items-center justify-end gap-2">
            <ScoreBadge cv={cv} />
            <MiniVoteButtons yourVote={row.your_vote ?? null} disabled={isVoting} onVote={onVote} />
          </div>
          <VoteBar cv={cv} />
        </div>
      </div>
    </div>
  );
}

function TabButton({
  active,
  children,
  onClick,
}: {
  active: boolean;
  children: React.ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-2xl px-3 py-1.5 text-xs border transition-colors ${
        active
          ? "border-slate-200/20 bg-slate-200/10 text-slate-100"
          : "border-slate-800 bg-slate-950/20 text-slate-300 hover:bg-slate-900/40"
      }`}
    >
      {children}
    </button>
  );
}

function StatRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-2xl border border-slate-800 bg-slate-950/20 px-4 py-2">
      <div className="text-xs text-slate-400">{label}</div>
      <div className="text-sm text-slate-100">{value}</div>
    </div>
  );
}

function getNotableTeam(n: DrawerNotable | null | undefined): string | null {
  if (!n) return null;

  const directKeys = [
    "team",
    "team_abbrev",
    "team_abbreviation",
    "team_code",
    "team_id",
    "team_name",
    "season_team",
    "best_team",
  ] as const;

  for (const k of directKeys) {
    const v = (n as any)?.[k];
    if (typeof v === "string" && v.trim()) return v.trim();
  }

  const visited = new Set<any>();

  function looksLikeTeamAbbrev(v: unknown): v is string {
    return typeof v === "string" && /^[A-Z]{2,4}$/.test(v.trim());
  }

  function walk(v: any): string | null {
    if (v == null) return null;
    if (looksLikeTeamAbbrev(v)) return v.trim();
    if (typeof v !== "object") return null;
    if (visited.has(v)) return null;
    visited.add(v);

    if (Array.isArray(v)) {
      for (const item of v) {
        const found = walk(item);
        if (found) return found;
      }
      return null;
    }

    for (const key of Object.keys(v)) {
      const found = walk(v[key]);
      if (found) return found;
    }
    return null;
  }

  return walk(n);
}

function TeamPill({ team }: { team: string }) {
  return (
    <span className="inline-flex items-center rounded-full border border-slate-700 bg-slate-950 px-2 py-0.5 text-[11px] text-slate-300">
      {team}
    </span>
  );
}

function DrawerTabView({ tab, positionGroup }: { tab: DrawerTab; positionGroup: string | null }) {
  const totals = tab.totals;
  const pg = (positionGroup ?? "").toUpperCase();

  const showPassing = totals.passing.att > 0 || pg === "QB";
  const showReceiving = totals.receiving.targets > 0 || ["WR", "TE", "REC"].includes(pg);
  const showRushing = totals.rushing.att > 0 || pg === "RB";
  const showDefense =
    totals.defense.tackles > 0 ||
    totals.defense.sacks > 0 ||
    totals.defense.int > 0 ||
    ["DB", "DL", "LB", "DEF"].includes(pg);

  return (
    <div className="space-y-4">
      <div className="rounded-3xl border border-slate-800 bg-slate-900/30 p-4">
        <div className="text-xs text-slate-500">Totals</div>
        <div className="mt-2 grid gap-2">
          <StatRow label="Games" value={totals.games} />

          {showReceiving ? (
            <>
              <StatRow label="Targets" value={totals.receiving.targets} />
              <StatRow label="Receptions" value={totals.receiving.rec} />
              <StatRow label="Rec Yards" value={totals.receiving.yds} />
              <StatRow label="Rec TD" value={totals.receiving.td} />
            </>
          ) : null}

          {showRushing ? (
            <>
              <StatRow label="Rush Att" value={totals.rushing.att} />
              <StatRow label="Rush Yards" value={totals.rushing.yds} />
              <StatRow label="Rush TD" value={totals.rushing.td} />
            </>
          ) : null}

          {showPassing ? (
            <>
              <StatRow label="Pass Att" value={totals.passing.att} />
              <StatRow label="Pass Yards" value={totals.passing.yds} />
              <StatRow label="Pass TD" value={totals.passing.td} />
              <StatRow label="INT" value={totals.passing.int} />
            </>
          ) : null}

          {showDefense ? (
            <>
              <StatRow label="Tackles" value={totals.defense.tackles} />
              <StatRow label="Sacks" value={totals.defense.sacks.toFixed(1)} />
              <StatRow label="INT" value={totals.defense.int} />
              <StatRow label="Def TD" value={totals.defense.td} />
            </>
          ) : null}

          <StatRow label="Fumbles Lost" value={totals.ball_security.fumbles_lost} />
        </div>
      </div>

      <div className="rounded-3xl border border-slate-800 bg-slate-900/30 p-4">
        <div className="text-xs text-slate-500">Notables</div>
        <div className="mt-3 space-y-2">
          {/* Best season */}
          <div className="rounded-2xl border border-slate-800 bg-slate-950/20 px-4 py-2">
            <div className="text-[11px] text-slate-500">Best season</div>
            <div className="mt-0.5 flex items-start justify-between gap-3">
              <div className="text-sm text-slate-100">
                {tab.notables.best_season?.headline ?? <span className="text-slate-500">—</span>}
              </div>

              {tab.scope !== "draft_team" && getNotableTeam(tab.notables.best_season) ? (
                <TeamPill team={getNotableTeam(tab.notables.best_season)!} />
              ) : null}
            </div>
          </div>

          {/* Best game */}
          <div className="rounded-2xl border border-slate-800 bg-slate-950/20 px-4 py-2">
            <div className="text-[11px] text-slate-500">Best game</div>
            <div className="mt-0.5 flex items-start justify-between gap-3">
              <div className="text-sm text-slate-100">
                {tab.notables.best_game?.headline ?? <span className="text-slate-500">—</span>}
              </div>

              {tab.scope !== "draft_team" && getNotableTeam(tab.notables.best_game) ? (
                <TeamPill team={getNotableTeam(tab.notables.best_game)!} />
              ) : null}
            </div>

            {tab.notables.best_game?.game_id ? (
              <div className="mt-1 font-mono text-[10px] text-slate-500">{tab.notables.best_game.game_id}</div>
            ) : null}
          </div>
        </div>
      </div>

      <div className="rounded-3xl border border-slate-800 bg-slate-900/30 p-4">
        <div className="text-xs text-slate-500">Scope</div>
        <div className="mt-2 text-xs text-slate-400">
          Teams:{" "}
          {tab.meta.teams_in_scope.length ? (
            <span className="text-slate-200">{tab.meta.teams_in_scope.join(", ")}</span>
          ) : (
            <span className="text-slate-500">—</span>
          )}
        </div>
        <div className="mt-1 text-xs text-slate-400">
          Seasons:{" "}
          {tab.meta.seasons_in_scope.length ? (
            <span className="text-slate-200">{tab.meta.seasons_in_scope.join(", ")}</span>
          ) : (
            <span className="text-slate-500">—</span>
          )}
        </div>
      </div>
    </div>
  );
}

function RankingsWindow({
  title,
  year,
  groupBy,
  sort = "best",
  minVotes = 1,
  limit = 32,
  defaultOpen = true,
}: {
  title: string;
  year: number;
  groupBy: "team" | "player";
  sort?: "best" | "worst";
  minVotes?: number;
  limit?: number;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = React.useState(defaultOpen);

  const query = useQuery({
    queryKey: ["rankings", groupBy, sort, year, minVotes, limit],
    queryFn: () => fetchRankings(year, groupBy, sort, minVotes, limit),
    enabled: open,
  });

  const items = query.data?.items ?? [];

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/30 overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-3 py-2 hover:bg-slate-800/40 transition-colors"
      >
        <span className="text-xs font-medium text-slate-300">{title}</span>
        <span className="text-[10px] text-slate-500">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div className="px-2 pb-2 space-y-0.5">
          {query.isLoading ? (
            <div className="px-1 py-2 text-xs text-slate-500">Loading…</div>
          ) : items.length === 0 ? (
            <div className="px-1 py-2 text-xs text-slate-500">No data yet for {year}.</div>
          ) : (
            items.map((item, i) => {
              const label = item.team ?? item.player ?? "—";
              const pct = item.ratio != null ? Math.round(item.ratio * 100) : null;
              return (
                <div
                  key={label + i}
                  className="flex items-center gap-2 rounded-xl px-2 py-1 hover:bg-slate-800/30"
                >
                  <span className="w-5 shrink-0 text-right text-[11px] text-slate-500">{i + 1}.</span>
                  <div className="flex-1 min-w-0">
                    <div className="truncate text-[11px] text-slate-200">{label}</div>
                    {item.draft_team && (
                      <div className="text-[10px] text-slate-500">{item.draft_team}</div>
                    )}
                  </div>
                  <span className="shrink-0 text-[11px] text-slate-300">{pct != null ? `${pct}%` : "—"}</span>
                  <span className="shrink-0 text-[10px] text-slate-500">({item.totalVotes})</span>
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}

function RankingsPanel({
  year,
  open,
  onToggle,
}: {
  year: number;
  open: boolean;
  onToggle: () => void;
}) {
  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 z-20 bg-black/40 transition-opacity ${open ? "opacity-100" : "opacity-0 pointer-events-none"}`}
        onClick={onToggle}
      />

      {/* Slide-in panel */}
      <aside
        className={`fixed top-0 left-0 z-30 h-full w-80 flex flex-col border-r border-slate-800 bg-slate-950 shadow-2xl transition-transform duration-200 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800 shrink-0">
          <span className="text-sm font-semibold text-slate-200">Rankings</span>
          <button
            type="button"
            onClick={onToggle}
            className="rounded-lg border border-slate-800 bg-slate-900/40 px-3 py-1.5 text-xs text-slate-400 hover:bg-slate-800/60 transition-colors"
          >
            Close
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          <RankingsWindow title="Team Success %" year={year} groupBy="team" sort="best" limit={32} />
          <RankingsWindow title="Best Picks" year={year} groupBy="player" sort="best" minVotes={2} limit={10} defaultOpen={false} />
          <RankingsWindow title="Biggest Busts" year={year} groupBy="player" sort="worst" minVotes={2} limit={10} defaultOpen={false} />
        </div>
      </aside>

      {/* Collapsed tab — visible when panel is closed */}
      {!open && (
        <button
          type="button"
          onClick={onToggle}
          className="fixed left-0 top-1/2 -translate-y-1/2 z-30 flex flex-col items-center gap-1 rounded-r-xl border border-l-0 border-slate-700 bg-slate-900 px-2 py-3 text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition-colors"
          title="Open rankings"
        >
          <span
            className="text-[10px] font-medium tracking-wide"
            style={{ writingMode: "vertical-rl", transform: "rotate(180deg)" }}
          >
            Rankings
          </span>
          <span className="text-[9px]">▲</span>
        </button>
      )}
    </>
  );
}

/** -----------------------------
 * Page
 * ------------------------------ */

function pickKey(year: number, overall: number): string {
  return `${year}:${overall}`;
}

export default function DraftBoardPage() {
  const PAGE_SIZE = 32;

  const years = React.useMemo(() => Array.from({ length: 26 }, (_, i) => 2000 + i), []);
  const mostRecentYear = years[years.length - 1];

  const [year, setYear] = React.useState<number>(mostRecentYear);
  const [round, setRound] = React.useState<number | null>(null);
  const [team, setTeam] = React.useState<string>("");
  const [pos, setPos] = React.useState<string>("");
  const [q, setQ] = React.useState<string>("");

  const [offset, setOffset] = React.useState<number>(0);
  const [selected, setSelected] = React.useState<{ year: number; overall: number } | null>(null);

  const [activeTab, setActiveTab] = React.useState<"career" | "draft_team" | "other_teams">("career");

  const [votingKeys, setVotingKeys] = React.useState<Set<string>>(() => new Set());
  const [rankingsPanelOpen, setRankingsPanelOpen] = React.useState(false);

  React.useEffect(() => {
    setOffset(0);
  }, [year, round, team, pos, q]);

  React.useEffect(() => {
    setActiveTab("career");
  }, [selected?.year, selected?.overall]);

  const boardQuery = useQuery({
    queryKey: ["draft", year, round, team, pos, q, offset, PAGE_SIZE],
    queryFn: () =>
      fetchDraftBoard({
        year,
        round,
        team: team || undefined,
        pos: pos || undefined,
        q: q || undefined,
        limit: PAGE_SIZE,
        offset,
      }),
  });

  const pickQuery = useQuery({
    queryKey: ["pick", selected?.year, selected?.overall],
    queryFn: () => fetchPickDetail(selected!.year, selected!.overall),
    enabled: !!selected,
  });

  const uniqueTeams = React.useMemo(() => {
    const rows = boardQuery.data ?? [];
    const map = new Map<string, string>();
    rows.forEach((r) => map.set(r.team.abbrev, `${r.team.abbrev} — ${r.team.city} ${r.team.name}`));
    return Array.from(map.entries()).sort((a, b) => a[0].localeCompare(b[0]));
  }, [boardQuery.data]);

  const uniquePositions = React.useMemo(() => {
    const rows = boardQuery.data ?? [];
    const set = new Set<string>();
    rows.forEach((r) => set.add(r.player.position));
    return Array.from(set).sort();
  }, [boardQuery.data]);

  const pageCount = boardQuery.data?.length ?? 0;
  const canPrev = offset > 0;
  const canNext = pageCount === PAGE_SIZE;

  async function voteForPick(args: { year: number; overall: number; value: "success" | "bust" }) {
    const key = pickKey(args.year, args.overall);
    if (votingKeys.has(key)) return;

    setVotingKeys((prev) => new Set(prev).add(key));
    try {
      await postVote(args.year, args.overall, args.value); // backend handles toggle-off when vote matches existing
      await boardQuery.refetch();
      if (selected && selected.year === args.year && selected.overall === args.overall) {
        await pickQuery.refetch();
      }
    } finally {
      setVotingKeys((prev) => {
        const next = new Set(prev);
        next.delete(key);
        return next;
      });
    }
  }

  // -------- Drawer endpoint wiring --------
  const drawerGsisId = React.useMemo(() => {
    const p: any = pickQuery.data;
    return (p?.player?.gsis_id ?? p?.player_career_summary?.gsis_id ?? p?.career_summary?.gsis_id ?? null) as
      | string
      | null;
  }, [pickQuery.data]);

  const drawerDraftTeam = pickQuery.data?.team?.abbrev ?? null;

  const drawerQuery = useQuery({
    queryKey: ["drawer", drawerGsisId, drawerDraftTeam],
    queryFn: () => fetchDrawer(drawerGsisId!, drawerDraftTeam!),
    enabled: !!drawerGsisId && !!drawerDraftTeam,
  });

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <RankingsPanel
        year={year}
        open={rankingsPanelOpen}
        onToggle={() => setRankingsPanelOpen((o) => !o)}
      />
      <div className="mx-auto max-w-5xl px-4 py-8">
        <div className="flex gap-3">
            <div className="flex flex-1 flex-col gap-1">
              <label className="text-xs text-slate-500">Year</label>
              <select
                className="w-full rounded-2xl border border-slate-800 bg-slate-900/40 px-3 py-2 text-sm"
                value={year}
                onChange={(e) => setYear(Number(e.target.value))}
              >
                {years.map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex flex-1 flex-col gap-1">
              <label className="text-xs text-slate-500">Round</label>
              <select
                className="w-full rounded-2xl border border-slate-800 bg-slate-900/40 px-3 py-2 text-sm"
                value={round ?? ""}
                onChange={(e) => setRound(e.target.value ? Number(e.target.value) : null)}
              >
                <option value="">All rounds</option>
                {[1, 2, 3, 4, 5, 6, 7].map((r) => (
                  <option key={r} value={r}>
                    Round {r}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex flex-2 flex-col gap-1">
              <label className="text-xs text-slate-500">Team</label>
              <select
                className="w-full rounded-2xl border border-slate-800 bg-slate-900/40 px-3 py-2 text-sm"
                value={team}
                onChange={(e) => setTeam(e.target.value)}
              >
                <option value="">All teams</option>
                {uniqueTeams.map(([abbrev, label]) => (
                  <option key={abbrev} value={abbrev}>
                    {label}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex flex-1 flex-col gap-1">
              <label className="text-xs text-slate-500">Pos</label>
              <select
                className="w-full rounded-2xl border border-slate-800 bg-slate-900/40 px-3 py-2 text-sm"
                value={pos}
                onChange={(e) => setPos(e.target.value)}
              >
                <option value="">All</option>
                {uniquePositions.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex flex-2 flex-col gap-1">
              <label className="text-xs text-slate-500">Search</label>
              <input
                className="w-full rounded-2xl border border-slate-800 bg-slate-900/40 px-3 py-2 text-sm"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Name / college…"
              />
            </div>
        </div>

        <div className="mt-6 flex items-center justify-between">
          <div className="text-xs text-slate-500">
            Showing {offset + 1}–{offset + (boardQuery.data?.length ?? 0)}
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={!canPrev}
              onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}
              className="rounded-2xl border border-slate-800 bg-slate-900/40 px-3 py-2 text-sm disabled:opacity-40"
            >
              Prev
            </button>
            <button
              type="button"
              disabled={!canNext}
              onClick={() => setOffset((o) => o + PAGE_SIZE)}
              className="rounded-2xl border border-slate-800 bg-slate-900/40 px-3 py-2 text-sm disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>

        <div className="mt-4 space-y-2">
          {boardQuery.isLoading ? (
            <div className="rounded-3xl border border-slate-800 bg-slate-900/30 p-6 text-slate-400">Loading…</div>
          ) : boardQuery.error ? (
            <div className="rounded-3xl border border-red-800/40 bg-red-950/20 p-6 text-red-200">
              {String(boardQuery.error)}
            </div>
          ) : (boardQuery.data ?? []).length === 0 ? (
            <div className="rounded-3xl border border-slate-800 bg-slate-900/30 p-6 text-slate-400">No results.</div>
          ) : (
            (boardQuery.data ?? []).map((r) => {
              const key = pickKey(r.year, r.overall);
              return (
                <Row
                  key={key}
                  row={r}
                  isVoting={votingKeys.has(key)}
                  onVote={(value) => voteForPick({ year: r.year, overall: r.overall, value })}
                  onOpen={() => setSelected({ year: r.year, overall: r.overall })}
                />
              );
            })
          )}
        </div>
      </div>

      <Drawer
        open={!!selected}
        onClose={() => setSelected(null)}
        title={
          pickQuery.data
            ? `#${pickQuery.data.overall} — ${pickQuery.data.player.full_name}`
            : selected
            ? `#${selected.overall}`
            : "Pick"
        }
      >
        {pickQuery.isLoading ? (
          <div className="text-sm text-slate-500">Loading…</div>
        ) : pickQuery.error ? (
          <div className="text-sm">
            <div className="font-semibold text-slate-100">Failed to load pick</div>
            <pre className="mt-4 text-xs overflow-auto rounded-2xl border border-slate-800 p-4 bg-slate-950/40">
              {String(pickQuery.error)}
            </pre>
          </div>
        ) : pickQuery.data ? (
          <div className="space-y-5">
            <div className="rounded-3xl border border-slate-800 bg-slate-900/30 p-5">
              <div className="text-xs text-slate-500">
                {pickQuery.data.year} • Round {pickQuery.data.round} • Pick {pickQuery.data.pick_in_round}
              </div>
              <div className="mt-2 text-xl font-semibold text-slate-100">{pickQuery.data.player.full_name}</div>

              <div className="mt-3 flex flex-wrap gap-2">
                <Pill variant={posVariant(pickQuery.data.player.position)}>{pickQuery.data.player.position}</Pill>
                {pickQuery.data.player.college ? (
                  <span className="inline-flex items-center rounded-full border border-slate-700 bg-slate-950 px-2 py-0.5 text-xs text-slate-300">
                    {pickQuery.data.player.college}
                  </span>
                ) : null}
                <span className="inline-flex items-center rounded-full border border-slate-700 bg-slate-950 px-2 py-0.5 text-xs text-slate-300">
                  {pickQuery.data.team.abbrev} — {pickQuery.data.team.city} {pickQuery.data.team.name}
                </span>
              </div>

              <div className="mt-5 flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <ScoreBadge cv={pickQuery.data.community_votes ?? null} />
                  {pickQuery.data.your_vote ? (
                    <span className="text-xs text-slate-400">You: {pickQuery.data.your_vote.value}</span>
                  ) : null}
                </div>
                <div className="flex gap-2">
                  <button
                    disabled={votingKeys.has(pickKey(pickQuery.data.year, pickQuery.data.overall))}
                    className="rounded-2xl border border-slate-800 bg-slate-900/40 px-4 py-2 text-sm text-slate-100 hover:bg-slate-800/60 disabled:opacity-50"
                    onClick={() =>
                      voteForPick({ year: pickQuery.data.year, overall: pickQuery.data.overall, value: "bust" })
                    }
                    type="button"
                  >
                    ❌ Bust
                  </button>
                  <button
                    disabled={votingKeys.has(pickKey(pickQuery.data.year, pickQuery.data.overall))}
                    className="rounded-2xl border border-slate-800 bg-slate-900/40 px-4 py-2 text-sm text-slate-100 hover:bg-slate-800/60 disabled:opacity-50"
                    onClick={() =>
                      voteForPick({ year: pickQuery.data.year, overall: pickQuery.data.overall, value: "success" })
                    }
                    type="button"
                  >
                    ✅ Success
                  </button>
                </div>
              </div>

              {(pickQuery.data.community_votes?.total ?? 0) === 0 ? (
                <div className="mt-3 text-xs text-slate-400">No votes yet — be the first to vote!</div>
              ) : null}

              <VoteBar cv={pickQuery.data.community_votes ?? null} />
            </div>

            <div className="rounded-3xl border border-slate-800 bg-slate-900/30 p-5">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="text-xs text-slate-500">Career snapshot</div>
                  <div className="text-sm text-slate-300">
                    {drawerGsisId ? (
                      <span className="font-mono text-[11px] text-slate-500">{drawerGsisId}</span>
                    ) : (
                      <span className="text-slate-500">No GSIS id on this pick yet.</span>
                    )}
                  </div>
                </div>

                <div className="flex gap-2">
                  <TabButton active={activeTab === "career"} onClick={() => setActiveTab("career")}>
                    Career
                  </TabButton>
                  <TabButton active={activeTab === "draft_team"} onClick={() => setActiveTab("draft_team")}>
                    Draft team
                  </TabButton>
                  <TabButton active={activeTab === "other_teams"} onClick={() => setActiveTab("other_teams")}>
                    Other teams
                  </TabButton>
                </div>
              </div>

              <div className="mt-4">
                {!drawerGsisId ? (
                  <div className="text-sm text-slate-500">
                    This pick detail response doesn’t include a GSIS id, so we can’t fetch career stats yet.
                  </div>
                ) : drawerQuery.isLoading ? (
                  <div className="text-sm text-slate-500">Loading career stats…</div>
                ) : drawerQuery.error ? (
                  <div className="text-sm">
                    <div className="font-semibold text-slate-100">Failed to load career stats</div>
                    <pre className="mt-4 text-xs overflow-auto rounded-2xl border border-slate-800 p-4 bg-slate-950/40">
                      {String(drawerQuery.error)}
                    </pre>
                  </div>
                ) : drawerQuery.data ? (
                  <DrawerTabView tab={drawerQuery.data.tabs[activeTab]} positionGroup={drawerQuery.data.player.position_group} />
                ) : (
                  <div className="text-sm text-slate-500">No stats available.</div>
                )}
              </div>
            </div>
          </div>
        ) : null}
      </Drawer>
    </div>
  );
}