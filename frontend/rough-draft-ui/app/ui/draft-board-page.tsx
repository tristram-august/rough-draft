// frontend/rough-draft-ui/app/ui/draft-board-page.tsx
"use client";

import * as React from "react";
import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../contexts/auth-context";

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
  voting_locked: boolean;
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
  voting_locked: boolean;
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

type CareerTimelineEntry = { season: number; team: string; games: number };

type OLSeasonStat = {
  season: number;
  position: string | null;
  team_abbrev: string | null;
  games: number | null;
  snap_counts_offense: number | null;
  pressures_allowed: number | null;
  hurries_allowed: number | null;
  hits_allowed: number | null;
  sacks_allowed: number | null;
  pbe: number | null;
  pass_block_percent: number | null;
  penalties: number | null;
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
  tabs: Record<string, DrawerTab>;
  timeline: CareerTimelineEntry[];
  selected_team: string | null;
  ol_stats: OLSeasonStat[];
  ui_hints: { default_tab: string };
};

type RankingsItem = {
  team?: string;
  player?: string;
  draft_team?: string | null;
  round?: number | null;
  overall?: number | null;
  success: number;
  bust: number;
  totalVotes: number;
  ratio: number | null;
};

type CommentOut = {
  id: number;
  pick_id: number;
  user_id: number;
  username: string;
  body: string;
  created_at: string;
  updated_at: string;
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
        className={`fixed inset-0 z-30 bg-black/50 transition-opacity ${open ? "opacity-100" : "opacity-0 pointer-events-none"}`}
        onClick={onClose}
      />
      <aside
        className={`fixed top-0 right-0 h-full w-full sm:max-w-xl z-30 border-l border-slate-800 bg-slate-950 text-slate-100 shadow-2xl transition-transform ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <div className="p-4 border-b border-slate-800 flex items-center justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="text-xs text-slate-500">Pick Detail</div>
            <div className="text-lg font-semibold leading-tight text-slate-100 truncate">{title}</div>
          </div>
          <button
            className="shrink-0 rounded-xl border border-slate-700 bg-slate-900/60 px-4 py-2 text-sm font-medium text-slate-200 hover:bg-slate-800/80 active:bg-slate-700 transition-colors"
            onClick={onClose}
            type="button"
          >
            ← Close
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

function authHeaders(token?: string | null): Record<string, string> {
  const h: Record<string, string> = { "X-Client-Id": getClientId() };
  if (token) h["Authorization"] = `Bearer ${token}`;
  return h;
}

async function fetchDraftTeams(year: number): Promise<Array<{ abbrev: string; city: string; name: string }>> {
  const res = await fetch(`${API_BASE}/draft/teams?year=${year}`, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

async function fetchDraftBoard(args: {
  year: number;
  round?: number | null;
  team?: string;
  pos?: string;
  q?: string;
  limit: number;
  offset: number;
  token?: string | null;
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
    headers: authHeaders(args.token),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Draft fetch failed: ${res.status}`);
  return res.json();
}

async function fetchPickDetail(year: number, overall: number, token?: string | null): Promise<PickDetail> {
  const res = await fetch(`${API_BASE}/pick/${year}/${overall}`, {
    headers: authHeaders(token),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Pick fetch failed: ${res.status}`);
  return res.json();
}

async function postVote(year: number, overall: number, value: "success" | "bust", token?: string | null): Promise<CommunityVotesOut> {
  const headers: Record<string, string> = {
    "X-Client-Id": getClientId(),
    "Content-Type": "application/json",
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}/pick/${year}/${overall}/vote`, {
    method: "POST",
    headers,
    body: JSON.stringify({ value }),
  });
  if (!res.ok) throw new Error(`Vote failed: ${res.status}`);
  return res.json();
}

async function fetchDrawer(gsisId: string, draftTeam: string, team?: string | null): Promise<DrawerResponse | null> {
  const url = new URL(`${API_BASE}/player/${gsisId}/drawer`);
  url.searchParams.set("draft_team", draftTeam);
  if (team) url.searchParams.set("team", team);

  const res = await fetch(url.toString(), { cache: "no-store" });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Drawer fetch failed: ${res.status}`);
  return res.json();
}

async function fetchComments(year: number, overall: number): Promise<CommentOut[]> {
  const res = await fetch(`${API_BASE}/pick/${year}/${overall}/comments`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Comments fetch failed: ${res.status}`);
  return res.json();
}

async function postComment(year: number, overall: number, body: string, token: string): Promise<CommentOut> {
  const res = await fetch(`${API_BASE}/pick/${year}/${overall}/comments`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ body }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to post comment");
  }
  return res.json();
}

async function deleteComment(commentId: number, token: string): Promise<void> {
  const res = await fetch(`${API_BASE}/comments/${commentId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to delete comment");
}

async function fetchRankings(
  year: number | null,
  groupBy: "team" | "player",
  sort: "best" | "worst" | "most_voted" | "controversial" = "best",
  minVotes: number = 1,
  limit: number = 32,
  minRound?: number,
  maxRound?: number,
): Promise<{ items: RankingsItem[] }> {
  const url = new URL(`${API_BASE}/rankings`);
  if (year !== null) url.searchParams.set("year", String(year));
  url.searchParams.set("groupBy", groupBy);
  url.searchParams.set("sort", sort);
  url.searchParams.set("minVotes", String(minVotes));
  url.searchParams.set("limit", String(limit));
  if (minRound != null) url.searchParams.set("minRound", String(minRound));
  if (maxRound != null) url.searchParams.set("maxRound", String(maxRound));
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
    "inline-flex h-7 w-7 items-center justify-center rounded-xl border text-xs leading-none transition-all disabled:opacity-50";

  function bustStyle(): React.CSSProperties {
    return active === "bust"
      ? { borderColor: "#ef4444", backgroundColor: "rgba(239,68,68,0.2)", color: "#fca5a5", boxShadow: "0 0 8px rgba(239,68,68,0.5)" }
      : { borderColor: "#475569", backgroundColor: "transparent", color: "#94a3b8" };
  }
  function successStyle(): React.CSSProperties {
    return active === "success"
      ? { borderColor: "#10b981", backgroundColor: "rgba(16,185,129,0.2)", color: "#6ee7b7", boxShadow: "0 0 8px rgba(16,185,129,0.5)" }
      : { borderColor: "#475569", backgroundColor: "transparent", color: "#94a3b8" };
  }

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
        className={base}
        style={bustStyle()}
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
        className={base}
        style={successStyle()}
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

const TEAM_COLORS: Record<string, string> = {
  ARI: "#97233F", ATL: "#A71930", BAL: "#241773", BUF: "#00338D",
  CAR: "#0085CA", CHI: "#C83803", CIN: "#FB4F14", CLE: "#FF3C00",
  DAL: "#003594", DEN: "#FB4F14", DET: "#0076B6", GB:  "#203731",
  HOU: "#C60C30", IND: "#002C5F", JAX: "#006778", KC:  "#E31837",
  LAC: "#0080C6", LAR: "#003594", LV:  "#A5ACAF", MIA: "#008E97",
  MIN: "#4F2683", NE:  "#002244", NO:  "#9F8958", NYG: "#0B2265",
  NYJ: "#125740", PHI: "#004C54", PIT: "#FFB612", SEA: "#69BE28",
  SF:  "#AA0000", TB:  "#D50A0A", TEN: "#4B92DB", WAS: "#5A1414",
  // Historical (relocated teams)
  SD:  "#0080C6", STL: "#003594", OAK: "#A5ACAF",
};

function teamColor(abbrev: string): string {
  return TEAM_COLORS[abbrev?.toUpperCase()] ?? "#475569";
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

  const [hovered, setHovered] = React.useState(false);
  const color = teamColor(row.team.abbrev);

  return (
    <div
      className="rounded-2xl border transition-colors px-4 py-3"
      style={{
        backgroundColor: color + (hovered ? "CC" : "AA"),
        borderColor: color,
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <div className="flex items-center gap-2 sm:gap-4">
        {/* Main click target (opens drawer) */}
        <button
          type="button"
          onClick={onOpen}
          className="flex min-w-0 flex-1 items-center gap-2 sm:gap-4 text-left"
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
                <span className="hidden sm:inline text-xs text-slate-400 truncate">{row.player.college}</span>
              ) : null}
            </div>
            <div className="mt-1 text-xs text-slate-500">
              <span className="text-slate-300">{row.team.abbrev}</span> — {row.team.city} {row.team.name}
              {row.outcome ? <span className="text-slate-500"> • Model: {row.outcome.label}</span> : null}
            </div>
          </div>
        </button>

        {/* Right column: score + mini buttons + bar */}
        <div className="w-32 sm:w-44 shrink-0">
          <div className="flex items-center justify-end gap-2">
            <ScoreBadge cv={cv} />
            <MiniVoteButtons yourVote={row.your_vote ?? null} disabled={isVoting || row.voting_locked} onVote={onVote} />
          </div>
          <VoteBar cv={cv} />
        </div>
      </div>
    </div>
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

function sumStat(rows: OLSeasonStat[], key: keyof OLSeasonStat): number {
  return rows.reduce((acc, r) => acc + (r[key] as number | null ?? 0), 0);
}
function avgStat(rows: OLSeasonStat[], key: keyof OLSeasonStat): number | null {
  const vals = rows.map(r => r[key] as number | null).filter((v): v is number => v != null);
  return vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null;
}

function OLDrawerView({ stats, selectedTeam }: { stats: OLSeasonStat[]; selectedTeam: string | null }) {
  const displayed = selectedTeam ? stats.filter(s => s.team_abbrev === selectedTeam) : stats;

  if (displayed.length === 0) {
    return (
      <div className="space-y-4">
        <div className="rounded-3xl border border-slate-800 bg-slate-900/30 p-4">
          <div className="text-xs text-slate-500">Totals</div>
          <div className="mt-2 text-sm text-slate-500">No blocking stats available{selectedTeam ? ` for ${selectedTeam}` : " (data starts 2006)"}.</div>
        </div>
      </div>
    );
  }

  const totalGames = sumStat(displayed, "games");
  const totalSnaps = sumStat(displayed, "snap_counts_offense");
  const totalPressures = sumStat(displayed, "pressures_allowed");
  const totalHurries = sumStat(displayed, "hurries_allowed");
  const totalHits = sumStat(displayed, "hits_allowed");
  const totalSacks = sumStat(displayed, "sacks_allowed");
  const totalPenalties = sumStat(displayed, "penalties");
  const avgPBE = avgStat(displayed, "pbe");

  const bestSeason = [...displayed].sort((a, b) => (b.pbe ?? 0) - (a.pbe ?? 0))[0];
  const teams = [...new Set(displayed.map(s => s.team_abbrev).filter(Boolean))];
  const seasons = displayed.map(s => s.season).sort((a, b) => a - b);

  return (
    <div className="space-y-4">
      {/* Totals */}
      <div className="rounded-3xl border border-slate-800 bg-slate-900/30 p-4">
        <div className="text-xs text-slate-500">Totals</div>
        <div className="mt-2 grid gap-2">
          <StatRow label="Games" value={totalGames} />
          <StatRow label="Snaps" value={totalSnaps} />
          <StatRow label="Pressures Allowed" value={totalPressures} />
          <StatRow label="Hurries Allowed" value={totalHurries} />
          <StatRow label="Hits Allowed" value={totalHits} />
          <StatRow label="Sacks Allowed" value={totalSacks} />
          <StatRow label="Penalties" value={totalPenalties} />
          <StatRow label="Avg PBE%" value={avgPBE != null ? avgPBE.toFixed(1) : "—"} />
        </div>
      </div>

      {/* Best season */}
      <div className="rounded-3xl border border-slate-800 bg-slate-900/30 p-4">
        <div className="text-xs text-slate-500">Notables</div>
        <div className="mt-3 space-y-2">
          <div className="rounded-2xl border border-slate-800 bg-slate-950/20 px-4 py-2">
            <div className="text-[11px] text-slate-500">Best season (PBE%)</div>
            <div className="mt-0.5 flex items-center justify-between gap-3">
              <div className="text-sm text-slate-100">
                {bestSeason.pbe != null
                  ? `${bestSeason.season}: ${bestSeason.pbe.toFixed(1)}% PBE, ${bestSeason.pressures_allowed ?? "—"} pressures`
                  : <span className="text-slate-500">—</span>}
              </div>
              {bestSeason.team_abbrev && !selectedTeam ? <TeamPill team={bestSeason.team_abbrev} /> : null}
            </div>
          </div>
        </div>
      </div>

      {/* Scope */}
      <div className="rounded-3xl border border-slate-800 bg-slate-900/30 p-4">
        <div className="text-xs text-slate-500">Scope</div>
        <div className="mt-2 text-xs text-slate-400">
          Teams: <span className="text-slate-200">{teams.join(", ") || "—"}</span>
        </div>
        <div className="mt-1 text-xs text-slate-400">
          Seasons: <span className="text-slate-200">{seasons.join(", ") || "—"}</span>
        </div>
        <div className="mt-1 text-xs text-slate-500">Stats available from 2006</div>
      </div>
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

function CareerTimeline({
  entries,
  selectedTeam,
  onSelect,
}: {
  entries: CareerTimelineEntry[];
  selectedTeam: string | null;
  onSelect: (team: string | null) => void;
}) {
  if (!entries.length) return null;

  const spans: { team: string; seasons: number[] }[] = [];
  for (const e of entries) {
    const last = spans[spans.length - 1];
    if (last && last.team === e.team) {
      last.seasons.push(e.season);
    } else {
      spans.push({ team: e.team, seasons: [e.season] });
    }
  }

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/30 p-4">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xs text-slate-500">Career Timeline</span>
        {selectedTeam && (
          <button
            type="button"
            onClick={() => onSelect(null)}
            className="rounded-full border border-slate-700 bg-slate-800 px-2 py-0.5 text-[10px] text-slate-300 hover:bg-slate-700 transition-colors"
          >
            All seasons
          </button>
        )}
      </div>
      <div className="flex flex-wrap gap-1">
        {spans.map((span, i) => {
          const color = teamColor(span.team);
          const isActive = selectedTeam === span.team;
          const label =
            span.seasons.length === 1
              ? `${span.seasons[0]}`
              : `${span.seasons[0]}–${span.seasons[span.seasons.length - 1]}`;
          return (
            <button
              type="button"
              key={i}
              onClick={() => onSelect(isActive ? null : span.team)}
              className="flex flex-col items-center rounded-xl px-2 py-1.5 border transition-all"
              style={{
                backgroundColor: color + (isActive ? "CC" : "33"),
                borderColor: color + (isActive ? "FF" : "88"),
                minWidth: `${Math.max(48, span.seasons.length * 18)}px`,
                boxShadow: isActive ? `0 0 0 2px ${color}` : "none",
              }}
              title={`${span.team} (${label}) — click to filter`}
            >
              <span className="text-[11px] font-semibold text-slate-100">{span.team}</span>
              <span className="text-[10px] text-slate-400">{label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function DrawerTabView({ tab, positionGroup }: { tab: DrawerTab; positionGroup: string | null }) {
  const totals = tab.totals;
  const pg = (positionGroup ?? "").toUpperCase();

  const isOL = pg === "OL";
  const showPassing = !isOL && (totals.passing.att > 0 || pg === "QB");
  const showReceiving = !isOL && (totals.receiving.targets > 0 || ["WR", "TE", "REC"].includes(pg));
  const showRushing = !isOL && (totals.rushing.att > 0 || pg === "RB");
  const showDefense = !isOL && ["DB", "DL", "LB", "DEF", "EDGE", "ED", "CB", "S"].includes(pg);
  const showFumbles = !isOL && !showDefense;

  if (isOL) return null;

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
              <StatRow label="Forced Fumbles" value={totals.defense.ff} />
              <StatRow label="Def TD" value={totals.defense.td} />
            </>
          ) : null}

          {showFumbles ? <StatRow label="Fumbles Lost" value={totals.ball_security.fumbles_lost} /> : null}
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

function CommentsSection({ year, overall }: { year: number; overall: number }) {
  const { user, token } = useAuth();
  const qc = useQueryClient();
  const commentsKey = ["comments", year, overall];

  const commentsQuery = useQuery({
    queryKey: commentsKey,
    queryFn: () => fetchComments(year, overall),
  });

  const [body, setBody] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);
  const [submitError, setSubmitError] = React.useState<string | null>(null);

  async function handlePost(e: React.SyntheticEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!token || !body.trim()) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      await postComment(year, overall, body.trim(), token);
      setBody("");
      qc.invalidateQueries({ queryKey: commentsKey });
    } catch (err: any) {
      setSubmitError(err.message ?? "Failed to post");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(commentId: number) {
    if (!token) return;
    try {
      await deleteComment(commentId, token);
      qc.invalidateQueries({ queryKey: commentsKey });
    } catch {
      // silently ignore
    }
  }

  const comments = commentsQuery.data ?? [];

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/30 p-5 space-y-4">
      <div className="text-xs text-slate-500">Community Comments</div>

      {/* Comment list */}
      {commentsQuery.isLoading ? (
        <div className="text-xs text-slate-500">Loading…</div>
      ) : comments.length === 0 ? (
        <div className="text-xs text-slate-500">No comments yet — be the first!</div>
      ) : (
        <div className="space-y-2">
          {comments.map((c) => (
            <div key={c.id} className="rounded-2xl border border-slate-800 bg-slate-950/30 px-4 py-3">
              <div className="flex items-center justify-between gap-2 mb-1">
                <Link href={`/profile/${c.username}`} className="text-xs font-medium text-slate-300 hover:text-slate-100 transition-colors">
                  {c.username}
                </Link>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-slate-600">
                    {new Date(c.created_at).toLocaleDateString()}
                  </span>
                  {(user?.user_id === c.user_id || user?.is_mod) && (
                    <button
                      type="button"
                      onClick={() => handleDelete(c.id)}
                      className="text-[10px] text-slate-600 hover:text-red-400 transition-colors"
                    >
                      delete
                    </button>
                  )}
                </div>
              </div>
              <div className="text-sm text-slate-200 whitespace-pre-wrap">{c.body}</div>
            </div>
          ))}
        </div>
      )}

      {/* Post form */}
      {user ? (
        <form onSubmit={handlePost} className="space-y-2">
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="Share your take…"
            rows={3}
            className="w-full rounded-2xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none focus:border-slate-500 resize-none"
          />
          {submitError && (
            <div className="text-xs text-red-400">{submitError}</div>
          )}
          <button
            type="submit"
            disabled={submitting || !body.trim()}
            className="rounded-2xl border border-slate-600 bg-slate-800 px-4 py-2 text-xs text-slate-100 hover:bg-slate-700 disabled:opacity-40 transition-colors"
          >
            {submitting ? "Posting…" : "Post comment"}
          </button>
        </form>
      ) : (
        <div className="text-xs text-slate-500">
          Sign in to leave a comment.
        </div>
      )}
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
  minRound,
  maxRound,
  defaultOpen = true,
}: {
  title: string;
  year: number | null;
  groupBy: "team" | "player";
  sort?: "best" | "worst" | "most_voted" | "controversial";
  minVotes?: number;
  limit?: number;
  minRound?: number;
  maxRound?: number;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = React.useState(defaultOpen);

  const query = useQuery({
    queryKey: ["rankings", groupBy, sort, year, minVotes, limit, minRound, maxRound],
    queryFn: () => fetchRankings(year, groupBy, sort, minVotes, limit, minRound, maxRound),
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
                    {(item.draft_team || item.round != null) && (
                      <div className="text-[10px] text-slate-500">
                        {item.draft_team}{item.round != null ? ` · Rd ${item.round} #${item.overall}` : ""}
                      </div>
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
  const [allTime, setAllTime] = React.useState(false);
  const effectiveYear = allTime ? null : year;

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
        <div className="flex items-center gap-2 px-4 py-2 border-b border-slate-800 shrink-0">
          <button
            type="button"
            onClick={() => setAllTime(false)}
            className={`rounded-lg px-3 py-1 text-xs transition-colors ${!allTime ? "bg-slate-700 text-slate-100" : "text-slate-500 hover:text-slate-300"}`}
          >
            {year}
          </button>
          <button
            type="button"
            onClick={() => setAllTime(true)}
            className={`rounded-lg px-3 py-1 text-xs transition-colors ${allTime ? "bg-slate-700 text-slate-100" : "text-slate-500 hover:text-slate-300"}`}
          >
            All Time
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          <RankingsWindow title="Team Success %" year={effectiveYear} groupBy="team" sort="best" limit={32} defaultOpen={false} />
          <RankingsWindow title="Best Picks" year={effectiveYear} groupBy="player" sort="best" minVotes={2} limit={10} defaultOpen={false} />
          <RankingsWindow title="Biggest Busts" year={effectiveYear} groupBy="player" sort="worst" minVotes={2} limit={10} defaultOpen={false} />
          <RankingsWindow title="Most Controversial" year={effectiveYear} groupBy="player" sort="controversial" minVotes={3} limit={10} defaultOpen={false} />
          <RankingsWindow title="Most Voted" year={effectiveYear} groupBy="player" sort="most_voted" minVotes={1} limit={10} defaultOpen={false} />
          <RankingsWindow title="Biggest Steals" year={effectiveYear} groupBy="player" sort="best" minVotes={2} limit={10} minRound={3} defaultOpen={false} />
          <RankingsWindow title="Biggest Reaches" year={effectiveYear} groupBy="player" sort="worst" minVotes={2} limit={10} maxRound={2} defaultOpen={false} />
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

  const years = React.useMemo(() => Array.from({ length: 27 }, (_, i) => 2000 + i), []);
  const mostRecentYear = 2025;

  const [year, setYear] = React.useState<number>(mostRecentYear);
  const [round, setRound] = React.useState<number | null>(null);
  const [team, setTeam] = React.useState<string>("");
  const [pos, setPos] = React.useState<string>("");
  const [q, setQ] = React.useState<string>("");

  const [offset, setOffset] = React.useState<number>(0);
  const [selected, setSelected] = React.useState<{ year: number; overall: number } | null>(null);

  const [selectedTeam, setSelectedTeam] = React.useState<string | null>(null);

  const { token } = useAuth();

  const [votingKeys, setVotingKeys] = React.useState<Set<string>>(() => new Set());
  const [rankingsPanelOpen, setRankingsPanelOpen] = React.useState(false);

  React.useEffect(() => {
    setOffset(0);
  }, [year, round, team, pos, q]);

  React.useEffect(() => {
    setSelectedTeam(null);
  }, [selected?.year, selected?.overall]);

  const boardQuery = useQuery({
    queryKey: ["draft", year, round, team, pos, q, offset, PAGE_SIZE, token],
    queryFn: () =>
      fetchDraftBoard({
        year,
        round,
        team: team || undefined,
        pos: pos || undefined,
        q: q || undefined,
        limit: PAGE_SIZE,
        offset,
        token,
      }),
  });

  const pickQuery = useQuery({
    queryKey: ["pick", selected?.year, selected?.overall, token],
    queryFn: () => fetchPickDetail(selected!.year, selected!.overall, token),
    enabled: !!selected,
  });

  const teamsQuery = useQuery({
    queryKey: ["draft-teams", year],
    queryFn: () => fetchDraftTeams(year),
    staleTime: 60_000,
  });
  const uniqueTeams: Array<[string, string]> = (teamsQuery.data ?? []).map(
    (t) => [t.abbrev, `${t.abbrev} — ${t.city} ${t.name}`]
  );

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
      await postVote(args.year, args.overall, args.value, token);
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
    queryKey: ["drawer", drawerGsisId, drawerDraftTeam, selectedTeam],
    queryFn: () => fetchDrawer(drawerGsisId!, drawerDraftTeam!, selectedTeam),
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
        <div className="grid grid-cols-2 sm:flex gap-3">
            <div className="flex flex-col gap-1 sm:flex-1">
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

            <div className="flex flex-col gap-1 sm:flex-1">
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

            <div className="flex flex-col gap-1 sm:flex-[2]">
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

            <div className="flex flex-col gap-1 sm:flex-1">
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

            <div className="col-span-2 flex flex-col gap-1 sm:flex-[2]">
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
              <div className="flex gap-4">
                {/* Headshot */}
                {drawerQuery.data?.player.headshot ? (
                  <img
                    src={drawerQuery.data.player.headshot}
                    alt={pickQuery.data.player.full_name}
                    className="h-24 w-24 shrink-0 rounded-2xl object-cover object-top border border-slate-700"
                  />
                ) : (
                  <div className="h-24 w-24 shrink-0 rounded-2xl border border-slate-700 bg-slate-800 flex items-center justify-center text-3xl text-slate-500">
                    ?
                  </div>
                )}

                {/* Player info */}
                <div className="min-w-0 flex-1">
                  <div className="text-xs text-slate-500">
                    {pickQuery.data.year} • Round {pickQuery.data.round} • Pick {pickQuery.data.pick_in_round}
                  </div>
                  <div className="mt-1 text-xl font-semibold text-slate-100 leading-tight">{pickQuery.data.player.full_name}</div>
                  <div className="mt-2 flex flex-wrap gap-2">
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
                </div>
              </div>

              <div className="mt-5 space-y-3">
                {/* Vote buttons */}
                {(() => {
                  const yourVote = pickQuery.data.your_vote?.value ?? null;
                  const isVoting = votingKeys.has(pickKey(pickQuery.data.year, pickQuery.data.overall));
                  const locked = pickQuery.data.voting_locked;
                  const bustActive = yourVote === "bust";
                  const successActive = yourVote === "success";
                  if (locked) {
                    return (
                      <div className="rounded-2xl border border-slate-800 bg-slate-900/30 px-4 py-3 text-center text-xs text-slate-500">
                        Voting opens after this class completes their first season
                      </div>
                    );
                  }
                  return (
                    <div className="flex gap-2">
                      <button
                        type="button"
                        disabled={isVoting}
                        onClick={() => voteForPick({ year: pickQuery.data.year, overall: pickQuery.data.overall, value: "bust" })}
                        className="flex-1 flex items-center justify-center gap-2 rounded-2xl border px-4 py-2.5 text-sm font-medium transition-all disabled:opacity-50"
                        style={bustActive
                          ? { borderColor: "#ef4444", backgroundColor: "rgba(239,68,68,0.15)", color: "#fca5a5", boxShadow: "0 0 12px rgba(239,68,68,0.3)" }
                          : { borderColor: "#334155", backgroundColor: "transparent", color: "#94a3b8" }}
                      >
                        <span>❌</span>
                        <span>Bust{bustActive ? " ✓" : ""}</span>
                      </button>
                      <button
                        type="button"
                        disabled={isVoting}
                        onClick={() => voteForPick({ year: pickQuery.data.year, overall: pickQuery.data.overall, value: "success" })}
                        className="flex-1 flex items-center justify-center gap-2 rounded-2xl border px-4 py-2.5 text-sm font-medium transition-all disabled:opacity-50"
                        style={successActive
                          ? { borderColor: "#10b981", backgroundColor: "rgba(16,185,129,0.15)", color: "#6ee7b7", boxShadow: "0 0 12px rgba(16,185,129,0.3)" }
                          : { borderColor: "#334155", backgroundColor: "transparent", color: "#94a3b8" }}
                      >
                        <span>✅</span>
                        <span>Success{successActive ? " ✓" : ""}</span>
                      </button>
                    </div>
                  );
                })()}

                {/* Score + bar */}
                <div className="flex items-center gap-3">
                  <ScoreBadge cv={pickQuery.data.community_votes ?? null} />
                  {(pickQuery.data.community_votes?.total ?? 0) === 0 && (
                    <span className="text-xs text-slate-500">No votes yet — be the first!</span>
                  )}
                </div>
                <VoteBar cv={pickQuery.data.community_votes ?? null} />
              </div>
            </div>

            {drawerQuery.data?.timeline?.length ? (
              <CareerTimeline
                entries={drawerQuery.data.timeline}
                selectedTeam={selectedTeam}
                onSelect={setSelectedTeam}
              />
            ) : null}

            <div className="rounded-3xl border border-slate-800 bg-slate-900/30 p-5">
              <div className="text-xs text-slate-500 mb-1">
                {selectedTeam ? `Stats with ${selectedTeam}` : "Career Stats"}
              </div>
              <div className="mt-2">
                {!drawerGsisId ? (
                  <div className="text-sm text-slate-500">No GSIS id on this pick yet.</div>
                ) : drawerQuery.isLoading ? (
                  <div className="text-sm text-slate-500">Loading…</div>
                ) : drawerQuery.error ? (
                  <div className="text-sm">
                    <div className="font-semibold text-slate-100">Failed to load stats</div>
                    <pre className="mt-4 text-xs overflow-auto rounded-2xl border border-slate-800 p-4 bg-slate-950/40">
                      {String(drawerQuery.error)}
                    </pre>
                  </div>
                ) : drawerQuery.data === null ? (
                  <div className="text-sm text-slate-500">No stats available yet — check back after the season.</div>
                ) : drawerQuery.data ? (
                  <>
                    <DrawerTabView
                      tab={drawerQuery.data.tabs[selectedTeam ? "selected" : "career"]}
                      positionGroup={drawerQuery.data.player.position_group}
                    />
                    {drawerQuery.data.player.position_group === "OL" && (
                      <OLDrawerView stats={drawerQuery.data.ol_stats ?? []} selectedTeam={selectedTeam} />
                    )}
                  </>
                ) : null}
              </div>
            </div>
            {selected && (
              <CommentsSection year={selected.year} overall={selected.overall} />
            )}
          </div>
        ) : null}
      </Drawer>
    </div>
  );
}