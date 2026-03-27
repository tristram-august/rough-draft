"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";

type TeamOut = {
  id: number;
  abbrev: string;
  name: string;
  city: string;
  conference?: string | null;
  division?: string | null;
};

type PlayerOut = {
  id: number;
  full_name: string;
  position: string;
  college?: string | null;
  birthdate?: string | null;
};

type OutcomeOut = {
  outcome_score: number;
  label: string;
  method_version: string;
  notes?: string | null;
};

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
  overall: number;
  pick_in_round: number;
  team: TeamOut;
  player: PlayerOut;
  traded_from_team?: TeamOut | null;
  outcome?: OutcomeOut | null;

  community_votes?: CommunityVotesOut | null;
  your_vote?: { value: "success" | "bust" } | null;
};

type PickDetail = DraftBoardRow & { notes?: string | null };

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

const NFL_TEAMS: Array<{ abbrev: string; label: string }> = [
  { abbrev: "ARI", label: "ARI — Arizona Cardinals" },
  { abbrev: "ATL", label: "ATL — Atlanta Falcons" },
  { abbrev: "BAL", label: "BAL — Baltimore Ravens" },
  { abbrev: "BUF", label: "BUF — Buffalo Bills" },
  { abbrev: "CAR", label: "CAR — Carolina Panthers" },
  { abbrev: "CHI", label: "CHI — Chicago Bears" },
  { abbrev: "CIN", label: "CIN — Cincinnati Bengals" },
  { abbrev: "CLE", label: "CLE — Cleveland Browns" },
  { abbrev: "DAL", label: "DAL — Dallas Cowboys" },
  { abbrev: "DEN", label: "DEN — Denver Broncos" },
  { abbrev: "DET", label: "DET — Detroit Lions" },
  { abbrev: "GB",  label: "GB — Green Bay Packers" },
  { abbrev: "HOU", label: "HOU — Houston Texans" },
  { abbrev: "IND", label: "IND — Indianapolis Colts" },
  { abbrev: "JAX", label: "JAX — Jacksonville Jaguars" },
  { abbrev: "KC",  label: "KC — Kansas City Chiefs" },
  { abbrev: "LAC", label: "LAC — Los Angeles Chargers" },
  { abbrev: "LAR", label: "LAR — Los Angeles Rams" },
  { abbrev: "LV",  label: "LV — Las Vegas Raiders" },
  { abbrev: "MIA", label: "MIA — Miami Dolphins" },
  { abbrev: "MIN", label: "MIN — Minnesota Vikings" },
  { abbrev: "NE",  label: "NE — New England Patriots" },
  { abbrev: "NO",  label: "NO — New Orleans Saints" },
  { abbrev: "NYG", label: "NYG — New York Giants" },
  { abbrev: "NYJ", label: "NYJ — New York Jets" },
  { abbrev: "PHI", label: "PHI — Philadelphia Eagles" },
  { abbrev: "PIT", label: "PIT — Pittsburgh Steelers" },
  { abbrev: "SEA", label: "SEA — Seattle Seahawks" },
  { abbrev: "SF",  label: "SF — San Francisco 49ers" },
  { abbrev: "TB",  label: "TB — Tampa Bay Buccaneers" },
  { abbrev: "TEN", label: "TEN — Tennessee Titans" },
  { abbrev: "WAS", label: "WAS — Washington Commanders" },
];

function getClientId(): string {
  if (typeof window === "undefined") return "server";
  const key = "roughdraft_client_id";
  const existing = window.localStorage.getItem(key);
  if (existing && existing.length >= 8) return existing;
  const created =
    globalThis.crypto?.randomUUID?.() ?? `rd_${Math.random().toString(16).slice(2)}_${Date.now()}`;
  window.localStorage.setItem(key, created);
  return created;
}

function cx(...xs: Array<string | false | null | undefined>): string {
  return xs.filter(Boolean).join(" ");
}

type PosVariant =
  | "qb"
  | "rb"
  | "wr"
  | "te"
  | "ol"
  | "dl"
  | "edge"
  | "lb"
  | "cb"
  | "s"
  | "st"
  | "other";

function posVariant(posRaw: string): PosVariant {
  const p0 = (posRaw || "").toUpperCase().trim();
  const parts = p0.split(/[^A-Z]+/).filter(Boolean);
  const has = (x: string) => parts.includes(x);

  if (has("QB")) return "qb";
  if (has("RB") || has("HB") || has("FB")) return "rb";
  if (has("WR")) return "wr";
  if (has("TE")) return "te";

  if (
    has("OL") ||
    has("OT") ||
    has("T") ||
    has("LT") ||
    has("RT") ||
    has("OG") ||
    has("G") ||
    has("LG") ||
    has("RG") ||
    has("C")
  )
    return "ol";

  if (has("EDGE")) return "edge";
  if (has("DE") && !has("DT")) return "edge";
  if (has("DL") || has("DT") || has("NT")) return "dl";

  if (has("LB") || has("ILB") || has("MLB")) return "lb";
  if (has("OLB") && !has("EDGE")) return "lb";

  if (has("CB")) return "cb";
  if (has("S") || has("FS") || has("SS")) return "s";
  if (has("DB") && !has("CB")) return "s";

  if (has("K") || has("PK") || has("P") || has("LS")) return "st";
  return "other";
}

function pillClass(variant?: PosVariant): string {
  switch (variant) {
    case "qb":
      return "border-blue-500/30 bg-blue-500/10 text-blue-200";
    case "rb":
      return "border-emerald-500/30 bg-emerald-500/10 text-emerald-200";
    case "wr":
      return "border-fuchsia-500/30 bg-fuchsia-500/10 text-fuchsia-200";
    case "te":
      return "border-indigo-500/30 bg-indigo-500/10 text-indigo-200";
    case "ol":
      return "border-amber-500/30 bg-amber-500/10 text-amber-200";
    case "edge":
      return "border-red-500/30 bg-red-500/10 text-red-200";
    case "dl":
      return "border-rose-500/30 bg-rose-500/10 text-rose-200";
    case "lb":
      return "border-orange-500/30 bg-orange-500/10 text-orange-200";
    case "cb":
      return "border-cyan-500/30 bg-cyan-500/10 text-cyan-200";
    case "s":
      return "border-teal-500/30 bg-teal-500/10 text-teal-200";
    case "st":
      return "border-slate-500/40 bg-slate-500/10 text-slate-200";
    default:
      return "border-slate-600/40 bg-slate-600/10 text-slate-200";
  }
}

function Pill({ children, variant }: { children: React.ReactNode; variant?: PosVariant }) {
  return (
    <span className={cx("inline-flex items-center rounded-full border px-2 py-0.5 text-xs", pillClass(variant))}>
      {children}
    </span>
  );
}

function ScoreBadge({ cv }: { cv?: CommunityVotesOut | null }) {
  const total = cv?.total ?? 0;
  if (!cv || total === 0) return <span className="text-xs text-slate-500">No votes</span>;

  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-slate-700 bg-slate-900/40 px-2 py-0.5 text-xs">
      <span className="font-semibold text-slate-100">{cv.community_score}%</span>
      <span className="text-slate-400">({total})</span>
    </span>
  );
}

function VoteBar({ cv }: { cv?: CommunityVotesOut | null }) {
  const total = cv?.total ?? 0;
  const pct = total ? cv!.community_score : 0;

  return (
    <div className="mt-1">
      <div className="h-2 w-full rounded-full bg-slate-800 overflow-hidden">
        <div className="h-full rounded-full bg-slate-200/70" style={{ width: `${pct}%` }} />
      </div>
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
        className={cx(
          "fixed inset-0 bg-black/50 transition-opacity",
          open ? "opacity-100" : "opacity-0 pointer-events-none"
        )}
        onClick={onClose}
      />
      <aside
        className={cx(
          "fixed right-0 top-0 h-full w-full max-w-md border-l border-slate-800 bg-slate-950 shadow-2xl transition-transform",
          open ? "translate-x-0" : "translate-x-full"
        )}
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

function Row({ row, onClick }: { row: DraftBoardRow; onClick: () => void }) {
  const cv = row.community_votes ?? null;

  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full text-left rounded-2xl border border-slate-800 bg-slate-900/30 hover:bg-slate-900/50 transition-colors px-4 py-3"
    >
      <div className="flex items-center gap-4">
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
            {row.player.college ? <span className="text-xs text-slate-400 truncate">{row.player.college}</span> : null}
          </div>
          <div className="mt-1 text-xs text-slate-500">
            <span className="text-slate-300">{row.team.abbrev}</span> — {row.team.city} {row.team.name}
            {row.outcome ? <span className="text-slate-500"> • Model: {row.outcome.label}</span> : null}
          </div>
        </div>

        <div className="w-36 shrink-0 text-right">
          <ScoreBadge cv={cv} />
          <VoteBar cv={cv} />
        </div>
      </div>
    </button>
  );
}

export default function DraftBoardPage() {
  const PAGE_SIZE = 32;

  // Year dropdown defaults to most recent available (2000..2025 => 2025)
  const years = React.useMemo(() => Array.from({ length: 26 }, (_, i) => 2000 + i), []);
  const mostRecentYear = years[years.length - 1];

  const [year, setYear] = React.useState<number>(mostRecentYear);
  const [round, setRound] = React.useState<number | null>(null); // All rounds by default
  const [team, setTeam] = React.useState<string>("");
  const [pos, setPos] = React.useState<string>("");
  const [q, setQ] = React.useState<string>("");

  const [offset, setOffset] = React.useState<number>(0);

  const [selected, setSelected] = React.useState<{ year: number; overall: number } | null>(null);

  // reset to first page whenever filters change
  React.useEffect(() => {
    setOffset(0);
  }, [year, round, team, pos, q]);

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

  async function handleVote(value: "success" | "bust") {
    if (!selected) return;
    await postVote(selected.year, selected.overall, value);
    await Promise.all([pickQuery.refetch(), boardQuery.refetch()]);
  }

  return (
    <div className="space-y-5">
      <div className="rounded-3xl border border-slate-800 bg-slate-900/30 p-5">
        <div className="flex flex-wrap items-end gap-4">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-slate-400">Year</label>
            <select
              className="h-11 w-32 rounded-2xl border border-slate-800 bg-slate-950 px-3 text-sm text-slate-100"
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

          <div className="flex flex-col gap-1">
            <label className="text-xs text-slate-400">Round</label>
            <select
              className="h-11 w-40 rounded-2xl border border-slate-800 bg-slate-950 px-3 text-sm text-slate-100"
              value={round ?? ""}
              onChange={(e) => setRound(e.target.value === "" ? null : Number(e.target.value))}
            >
              <option value="">All rounds</option>
              {Array.from({ length: 7 }).map((_, i) => (
                <option key={i + 1} value={i + 1}>
                  Round {i + 1}
                </option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs text-slate-400">Team</label>
            <select
              className="h-11 w-72 rounded-2xl border border-slate-800 bg-slate-950 px-3 text-sm text-slate-100"
              value={team}
              onChange={(e) => setTeam(e.target.value)}
            >
              <option value="">All teams</option>
              {NFL_TEAMS.map((t) => (
                <option key={t.abbrev} value={t.abbrev}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs text-slate-400">Position</label>
            <select
              className="h-11 w-44 rounded-2xl border border-slate-800 bg-slate-950 px-3 text-sm text-slate-100"
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

          <div className="flex-1 min-w-[240px] flex flex-col gap-1">
            <label className="text-xs text-slate-400">Search</label>
            <input
              className="h-11 rounded-2xl border border-slate-800 bg-slate-950 px-3 text-sm text-slate-100 placeholder:text-slate-600"
              placeholder="Player, college, team…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </div>

          <button
            className="h-11 rounded-2xl border border-slate-800 bg-slate-900/40 px-5 text-sm text-slate-100 hover:bg-slate-800/60"
            onClick={() => boardQuery.refetch()}
            type="button"
          >
            Refresh
          </button>
        </div>

        <div className="mt-4 text-xs text-slate-500">
          {boardQuery.isLoading ? "Loading…" : boardQuery.error ? "Error loading board" : `${pageCount} picks this page`}
        </div>
      </div>

      {/* ✅ Paginator controls go HERE: between filters and the list */}
      <div className="flex items-center justify-between gap-3">
        <div className="text-xs text-slate-500">
          Showing {offset + 1}–{offset + pageCount}
          {round ? ` • Round ${round}` : " • All rounds"} • Page size {PAGE_SIZE}
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            className="h-10 rounded-2xl border border-slate-800 bg-slate-900/40 px-4 text-sm text-slate-100 hover:bg-slate-800/60 disabled:opacity-40 disabled:hover:bg-slate-900/40"
            disabled={!canPrev}
            onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}
          >
            Prev
          </button>
          <button
            type="button"
            className="h-10 rounded-2xl border border-slate-800 bg-slate-900/40 px-4 text-sm text-slate-100 hover:bg-slate-800/60 disabled:opacity-40 disabled:hover:bg-slate-900/40"
            disabled={!canNext}
            onClick={() => setOffset((o) => o + PAGE_SIZE)}
          >
            Next
          </button>
        </div>
      </div>

      {boardQuery.error ? (
        <div className="rounded-3xl border border-slate-800 bg-slate-900/30 p-5 text-sm">
          <div className="font-semibold text-slate-100">Failed to load</div>
          <div className="text-slate-400 mt-2">
            Make sure FastAPI is running and <span className="font-mono">{API_BASE}</span> is reachable.
          </div>
          <pre className="mt-4 text-xs overflow-auto rounded-2xl border border-slate-800 p-4 bg-slate-950/40">
            {String(boardQuery.error)}
          </pre>
        </div>
      ) : (
        <div className="space-y-3">
          {(boardQuery.data ?? []).map((r) => (
            <Row key={`${r.year}-${r.overall}`} row={r} onClick={() => setSelected({ year: r.year, overall: r.overall })} />
          ))}
          {boardQuery.isLoading ? <div className="text-sm text-slate-500">Loading…</div> : null}
        </div>
      )}

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
                    className="rounded-2xl border border-slate-800 bg-slate-900/40 px-4 py-2 text-sm text-slate-100 hover:bg-slate-800/60"
                    onClick={() => handleVote("success")}
                    type="button"
                  >
                    ✅ Success
                  </button>
                  <button
                    className="rounded-2xl border border-slate-800 bg-slate-900/40 px-4 py-2 text-sm text-slate-100 hover:bg-slate-800/60"
                    onClick={() => handleVote("bust")}
                    type="button"
                  >
                    ❌ Bust
                  </button>
                </div>
              </div>

              <VoteBar cv={pickQuery.data.community_votes ?? null} />
            </div>
          </div>
        ) : null}
      </Drawer>
    </div>
  );
}