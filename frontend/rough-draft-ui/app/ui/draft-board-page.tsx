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

  // if you patched backend /draft to include it, it'll show on cards too
  community_votes?: CommunityVotesOut | null;
  your_vote?: { value: "success" | "bust" } | null;
};

type PickDetail = DraftBoardRow & { notes?: string | null };

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

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

function buildDraftUrl(params: {
  year: number;
  round?: number | null;
  team?: string;
  pos?: string;
  q?: string;
}): string {
  const url = new URL(`${API_BASE}/draft`);
  url.searchParams.set("year", String(params.year));
  if (params.round) url.searchParams.set("round", String(params.round));
  if (params.team) url.searchParams.set("team", params.team);
  if (params.pos) url.searchParams.set("pos", params.pos);
  if (params.q) url.searchParams.set("q", params.q);
  url.searchParams.set("limit", "400");
  url.searchParams.set("offset", "0");
  return url.toString();
}

async function fetchDraftBoard(args: {
  year: number;
  round?: number | null;
  team?: string;
  pos?: string;
  q?: string;
}): Promise<DraftBoardRow[]> {
  const res = await fetch(buildDraftUrl(args), {
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

  // handle composites like "WR/RB", "CB/S", "G/T"
  const parts = p0.split(/[^A-Z]+/).filter(Boolean);
  const has = (x: string) => parts.includes(x);

  if (has("QB")) return "qb";

  if (has("RB") || has("HB") || has("FB")) return "rb";
  if (has("WR")) return "wr";
  if (has("TE")) return "te";

  // OL
  if (has("OL") || has("OT") || has("T") || has("LT") || has("RT") || has("OG") || has("G") || has("LG") || has("RG") || has("C"))
    return "ol";

  // DL/EDGE/LB
  if (has("EDGE")) return "edge";
  if (has("DE") && !has("DT")) return "edge"; // common shorthand
  if (has("DL") || has("DT") || has("NT")) return "dl";

  if (has("LB") || has("ILB") || has("MLB")) return "lb";
  if (has("OLB") && !has("EDGE")) return "lb"; // some datasets use OLB as LB

  // DB
  if (has("CB")) return "cb";
  if (has("S") || has("FS") || has("SS")) return "s";
  if (has("DB") && !has("CB")) return "s";

  // Special teams
  if (has("K") || has("PK")) return "st";
  if (has("P")) return "st";
  if (has("LS")) return "st";

  return "other";
}

function pillClass(variant?: PosVariant): string {
  // explicit classes (tailwind-safe)
  switch (variant) {
    case "qb":
      return "border-blue-200 bg-blue-50 text-blue-800";
    case "rb":
      return "border-green-200 bg-green-50 text-green-800";
    case "wr":
      return "border-purple-200 bg-purple-50 text-purple-800";
    case "te":
      return "border-indigo-200 bg-indigo-50 text-indigo-800";
    case "ol":
      return "border-amber-200 bg-amber-50 text-amber-900";
    case "edge":
      return "border-red-200 bg-red-50 text-red-800";
    case "dl":
      return "border-rose-200 bg-rose-50 text-rose-800";
    case "lb":
      return "border-orange-200 bg-orange-50 text-orange-900";
    case "cb":
      return "border-cyan-200 bg-cyan-50 text-cyan-800";
    case "s":
      return "border-teal-200 bg-teal-50 text-teal-800";
    case "st":
      return "border-slate-200 bg-slate-50 text-slate-700";
    default:
      return "border-slate-200 bg-slate-50 text-slate-700";
  }
}

function Pill({ children, variant }: { children: React.ReactNode; variant?: PosVariant }) {
  return (
    <span className={cx("inline-flex items-center rounded-full border px-2 py-0.5 text-xs", pillClass(variant))}>
      {children}
    </span>
  );
}

function TeamChip({ team }: { team: TeamOut }) {
  return (
    <span className="inline-flex items-center rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs text-slate-700">
      {team.abbrev}
    </span>
  );
}

function ScoreBadge({ cv }: { cv?: CommunityVotesOut | null }) {
  const total = cv?.total ?? 0;
  if (!cv || total === 0) return <span className="text-xs text-slate-500">No votes</span>;

  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-2 py-0.5 text-xs">
      <span className="font-semibold text-slate-900">{cv.community_score}%</span>
      <span className="text-slate-500">({total})</span>
      <span className="text-slate-500">{cv.community_label}</span>
    </span>
  );
}

function VoteBar({ cv }: { cv?: CommunityVotesOut | null }) {
  const total = cv?.total ?? 0;
  const pct = total ? cv!.community_score : 0;

  return (
    <div className="mt-3">
      <div className="flex items-center justify-between text-[11px] text-slate-500">
        <span>{total ? `${pct}% success` : "No votes yet"}</span>
        <span>{total ? `${total} vote${total === 1 ? "" : "s"}` : ""}</span>
      </div>
      <div className="mt-1 h-2 w-full rounded-full bg-slate-100 overflow-hidden">
        <div className="h-full rounded-full bg-slate-900/70" style={{ width: `${pct}%` }} />
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
          "fixed inset-0 bg-black/40 transition-opacity",
          open ? "opacity-100" : "opacity-0 pointer-events-none"
        )}
        onClick={onClose}
      />
      <aside
        className={cx(
          "fixed right-0 top-0 h-full w-full max-w-md bg-white border-l border-slate-200 shadow-2xl transition-transform",
          open ? "translate-x-0" : "translate-x-full"
        )}
      >
        <div className="p-4 border-b border-slate-200 flex items-start justify-between gap-3">
          <div>
            <div className="text-xs text-slate-500">Pick Detail</div>
            <div className="text-lg font-semibold leading-tight text-slate-900">{title}</div>
          </div>
          <button
            className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm hover:bg-slate-50"
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

function PickCard({ row, onClick }: { row: DraftBoardRow; onClick: () => void }) {
  const cv = row.community_votes ?? null;
  const you = row.your_vote?.value;

  return (
    <button
      type="button"
      onClick={onClick}
      className="group text-left rounded-2xl border border-slate-200 bg-white shadow-sm hover:shadow-md transition-all hover:-translate-y-0.5 p-5"
    >
      <div className="flex items-start gap-4">
        <div className="shrink-0">
          <div className="h-14 w-14 rounded-2xl border border-slate-200 bg-slate-50 flex items-center justify-center font-mono text-base text-slate-900">
            {row.overall}
          </div>
          <div className="mt-2 text-[11px] text-slate-500 text-center">
            R{row.round}P{row.pick_in_round}
          </div>
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 min-w-0">
              <TeamChip team={row.team} />
              {you ? <span className="text-[11px] text-slate-500">You: {you}</span> : null}
            </div>
            <ScoreBadge cv={cv} />
          </div>

          <div className="mt-3">
            <div className="text-lg font-semibold leading-tight text-slate-900 truncate group-hover:underline">
              {row.player.full_name}
            </div>
            <div className="mt-2 flex flex-wrap gap-2">
              <Pill variant={posVariant(row.player.position)}>{row.player.position}</Pill>
              {row.player.college ? (
                <span className="inline-flex items-center rounded-full border border-slate-200 bg-white px-2 py-0.5 text-xs text-slate-600">
                  {row.player.college}
                </span>
              ) : null}
            </div>
          </div>

          <div className="mt-3 text-sm text-slate-600 truncate">
            {row.team.city} {row.team.name}
            {row.outcome ? (
              <span className="text-slate-400"> • Model: {row.outcome.label} ({row.outcome.outcome_score}/100)</span>
            ) : null}
          </div>

          <VoteBar cv={cv} />
        </div>
      </div>
    </button>
  );
}

export default function DraftBoardPage() {
  // Comfy view: 3 columns on lg screens, generous spacing
  const years = React.useMemo(() => Array.from({ length: 26 }, (_, i) => 2000 + i), []);

  const [year, setYear] = React.useState<number>(2000);
  const [round, setRound] = React.useState<number | null>(1);
  const [team, setTeam] = React.useState<string>("");
  const [pos, setPos] = React.useState<string>("");
  const [q, setQ] = React.useState<string>("");

  const [selected, setSelected] = React.useState<{ year: number; overall: number } | null>(null);

  const boardQuery = useQuery({
    queryKey: ["draft", year, round, team, pos, q],
    queryFn: () => fetchDraftBoard({ year, round, team: team || undefined, pos: pos || undefined, q: q || undefined }),
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

  async function handleVote(value: "success" | "bust") {
    if (!selected) return;
    await postVote(selected.year, selected.overall, value);
    await Promise.all([pickQuery.refetch(), boardQuery.refetch()]);
  }

  return (
    <div className="space-y-5">
      <div className="rounded-3xl border border-slate-200 bg-white shadow-sm p-5">
        <div className="flex flex-wrap items-end gap-4">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-slate-600">Year</label>
            <select
              className="h-11 w-32 rounded-2xl border border-slate-200 bg-white px-3 text-sm"
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
            <label className="text-xs text-slate-600">Round</label>
            <select
              className="h-11 w-40 rounded-2xl border border-slate-200 bg-white px-3 text-sm"
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
            <label className="text-xs text-slate-600">Team</label>
            <select
              className="h-11 w-72 rounded-2xl border border-slate-200 bg-white px-3 text-sm"
              value={team}
              onChange={(e) => setTeam(e.target.value)}
            >
              <option value="">All teams</option>
              {uniqueTeams.map(([abbr, label]) => (
                <option key={abbr} value={abbr}>
                  {label}
                </option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs text-slate-600">Position</label>
            <select
              className="h-11 w-44 rounded-2xl border border-slate-200 bg-white px-3 text-sm"
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
            <label className="text-xs text-slate-600">Search</label>
            <input
              className="h-11 rounded-2xl border border-slate-200 bg-white px-3 text-sm"
              placeholder="Player, college, team…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </div>

          <button
            className="h-11 rounded-2xl border border-slate-200 bg-white px-5 text-sm hover:bg-slate-50"
            onClick={() => boardQuery.refetch()}
            type="button"
          >
            Refresh
          </button>
        </div>

        <div className="mt-4 text-xs text-slate-500">
          {boardQuery.isLoading ? "Loading…" : boardQuery.error ? "Error loading board" : `${boardQuery.data?.length ?? 0} picks`}
        </div>
      </div>

      {boardQuery.error ? (
        <div className="rounded-3xl border border-slate-200 bg-white p-5 text-sm">
          <div className="font-semibold text-slate-900">Failed to load</div>
          <div className="text-slate-600 mt-2">
            Make sure FastAPI is running and <span className="font-mono">{API_BASE}</span> is reachable.
          </div>
          <pre className="mt-4 text-xs overflow-auto rounded-2xl border border-slate-200 p-4 bg-slate-50">
            {String(boardQuery.error)}
          </pre>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {(boardQuery.data ?? []).map((r) => (
            <PickCard
              key={`${r.year}-${r.overall}`}
              row={r}
              onClick={() => setSelected({ year: r.year, overall: r.overall })}
            />
          ))}
          {boardQuery.isLoading ? <div className="text-sm text-slate-500 col-span-full">Loading…</div> : null}
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
            <div className="font-semibold text-slate-900">Failed to load pick</div>
            <pre className="mt-4 text-xs overflow-auto rounded-2xl border border-slate-200 p-4 bg-slate-50">
              {String(pickQuery.error)}
            </pre>
          </div>
        ) : pickQuery.data ? (
          <div className="space-y-5">
            <div className="rounded-3xl border border-slate-200 bg-white p-5">
              <div className="text-xs text-slate-500">
                {pickQuery.data.year} • Round {pickQuery.data.round} • Pick {pickQuery.data.pick_in_round}
              </div>
              <div className="mt-2 text-xl font-semibold text-slate-900">{pickQuery.data.player.full_name}</div>

              <div className="mt-3 flex flex-wrap gap-2">
                <Pill variant={posVariant(pickQuery.data.player.position)}>{pickQuery.data.player.position}</Pill>
                {pickQuery.data.player.college ? (
                  <span className="inline-flex items-center rounded-full border border-slate-200 bg-white px-2 py-0.5 text-xs text-slate-600">
                    {pickQuery.data.player.college}
                  </span>
                ) : null}
                <span className="inline-flex items-center rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs text-slate-700">
                  {pickQuery.data.team.abbrev} — {pickQuery.data.team.city} {pickQuery.data.team.name}
                </span>
              </div>

              <div className="mt-5 flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <ScoreBadge cv={pickQuery.data.community_votes ?? null} />
                  {pickQuery.data.your_vote ? (
                    <span className="text-xs text-slate-500">You: {pickQuery.data.your_vote.value}</span>
                  ) : null}
                </div>
                <div className="flex gap-2">
                  <button
                    className="rounded-2xl border border-slate-200 bg-white px-4 py-2 text-sm hover:bg-slate-50"
                    onClick={() => handleVote("success")}
                    type="button"
                  >
                    ✅ Success
                  </button>
                  <button
                    className="rounded-2xl border border-slate-200 bg-white px-4 py-2 text-sm hover:bg-slate-50"
                    onClick={() => handleVote("bust")}
                    type="button"
                  >
                    ❌ Bust
                  </button>
                </div>
              </div>

              <VoteBar cv={pickQuery.data.community_votes ?? null} />
            </div>

            <div className="rounded-3xl border border-slate-200 bg-white p-5">
              <div className="text-sm font-semibold text-slate-900">Model outcome</div>
              <div className="mt-3">
                {pickQuery.data.outcome ? (
                  <div className="flex items-center gap-2">
                    <span className="inline-flex items-center rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs text-slate-700">
                      {pickQuery.data.outcome.label}
                    </span>
                    <span className="text-sm text-slate-600">
                      {pickQuery.data.outcome.outcome_score}/100 ({pickQuery.data.outcome.method_version})
                    </span>
                  </div>
                ) : (
                  <div className="text-sm text-slate-500">No model score yet.</div>
                )}
              </div>

              {pickQuery.data.notes ? (
                <div className="mt-4 text-xs text-slate-500">
                  Notes: <span className="font-mono">{pickQuery.data.notes}</span>
                </div>
              ) : null}
            </div>
          </div>
        ) : null}
      </Drawer>
    </div>
  );
}