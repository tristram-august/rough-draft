"use client";

import * as React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";
const PAGE_SIZE = 25;

const TEAM_COLORS: Record<string, string> = {
  ARI: "#97233F", ATL: "#A71930", BAL: "#241773", BUF: "#00338D",
  CAR: "#0085CA", CHI: "#C83803", CIN: "#FB4F14", CLE: "#FF3C00",
  DAL: "#003594", DEN: "#FB4F14", DET: "#0076B6", GB:  "#203731",
  HOU: "#C60C30", IND: "#002C5F", JAX: "#006778", KC:  "#E31837",
  LAC: "#0080C6", LAR: "#003594", LV:  "#A5ACAF", MIA: "#008E97",
  MIN: "#4F2683", NE:  "#002244", NO:  "#9F8958", NYG: "#0B2265",
  NYJ: "#125740", PHI: "#004C54", PIT: "#FFB612", SEA: "#69BE28",
  SF:  "#AA0000", TB:  "#D50A0A", TEN: "#4B92DB", WAS: "#5A1414",
  SD:  "#0080C6", STL: "#003594", OAK: "#A5ACAF",
};
function teamColor(abbrev: string) {
  return TEAM_COLORS[abbrev?.toUpperCase()] ?? "#475569";
}

type ProfileVote = {
  year: number; overall: number; pick_in_round: number; round: number;
  player_name: string; team_abbrev: string; value: "success" | "bust"; voted_at: string;
};
type ProfileComment = {
  id: number; year: number; overall: number; pick_in_round: number; round: number;
  player_name: string; team_abbrev: string; body: string; created_at: string;
};
type Profile = {
  username: string; joined_at: string;
  total_votes: number; total_success: number; total_bust: number; total_comments: number;
  votes: ProfileVote[]; comments: ProfileComment[];
};

async function fetchProfile(username: string, votesOffset: number, commentsOffset: number, voteFilter: "all" | "success" | "bust"): Promise<Profile> {
  const url = new URL(`${API_BASE}/profile/${encodeURIComponent(username)}`);
  url.searchParams.set("votesOffset", String(votesOffset));
  url.searchParams.set("commentsOffset", String(commentsOffset));
  if (voteFilter !== "all") url.searchParams.set("voteFilter", voteFilter);
  const res = await fetch(url.toString(), { cache: "no-store" });
  if (res.status === 404) throw new Error("User not found");
  if (!res.ok) throw new Error("Failed to load profile");
  return res.json();
}

function VoteChip({ value }: { value: "success" | "bust" }) {
  const base = "inline-flex w-20 items-center justify-center gap-1 rounded-full border px-2 py-0.5 text-[11px] shrink-0";
  return value === "success"
    ? <span className={`${base} border-emerald-800/50 bg-emerald-950/40 text-emerald-300`}>✅ Success</span>
    : <span className={`${base} border-red-800/50 bg-red-950/40 text-red-300`}>❌ Bust</span>;
}

function PickCard({ year, overall, round, pick_in_round, player_name, team_abbrev }: {
  year: number; overall: number; round: number; pick_in_round: number;
  player_name: string; team_abbrev: string;
}) {
  const color = teamColor(team_abbrev);
  return (
    <div className="rounded-xl border px-3 py-2" style={{ backgroundColor: color + "33", borderColor: color + "88" }}>
      <div className="flex items-center gap-2">
        <span className="font-mono text-xs text-slate-400">#{overall}</span>
        <span className="text-sm font-medium text-slate-100">{player_name}</span>
        <span className="text-xs text-slate-400">{team_abbrev}</span>
      </div>
      <div className="text-[10px] text-slate-500 mt-0.5">{year} · R{round}P{pick_in_round}</div>
    </div>
  );
}

function Pager({ offset, total, onPrev, onNext }: {
  offset: number; total: number; onPrev: () => void; onNext: () => void;
}) {
  const page = Math.floor(offset / PAGE_SIZE) + 1;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  if (totalPages <= 1) return null;
  return (
    <div className="flex items-center justify-between pt-2">
      <button
        type="button"
        disabled={offset === 0}
        onClick={onPrev}
        className="rounded-xl border border-slate-800 bg-slate-900/40 px-3 py-1.5 text-xs text-slate-300 disabled:opacity-30 hover:bg-slate-800/60 transition-colors"
      >
        ← Prev
      </button>
      <span className="text-xs text-slate-500">Page {page} of {totalPages}</span>
      <button
        type="button"
        disabled={offset + PAGE_SIZE >= total}
        onClick={onNext}
        className="rounded-xl border border-slate-800 bg-slate-900/40 px-3 py-1.5 text-xs text-slate-300 disabled:opacity-30 hover:bg-slate-800/60 transition-colors"
      >
        Next →
      </button>
    </div>
  );
}

export default function ProfilePage({ username }: { username: string }) {
  const [tab, setTab] = React.useState<"votes" | "comments">("votes");
  const [votesOffset, setVotesOffset] = React.useState(0);
  const [commentsOffset, setCommentsOffset] = React.useState(0);
  const [voteFilter, setVoteFilter] = React.useState<"all" | "success" | "bust">("all");

  function changeFilter(f: "all" | "success" | "bust") {
    setVoteFilter(f);
    setVotesOffset(0);
    setTab("votes");
  }

  const query = useQuery({
    queryKey: ["profile", username, votesOffset, commentsOffset, voteFilter],
    queryFn: () => fetchProfile(username, votesOffset, commentsOffset, voteFilter),
    staleTime: 0,
  });

  if (query.isLoading) {
    return <div className="text-slate-400 text-sm pt-8">Loading…</div>;
  }
  if (query.error) {
    return (
      <div className="rounded-3xl border border-red-800/40 bg-red-950/20 p-6 text-red-300 text-sm">
        {String(query.error)}
      </div>
    );
  }

  const profile = query.data;
  if (!profile) return <div className="text-slate-400 text-sm pt-8">Loading…</div>;
  const joinedYear = new Date(profile.joined_at).getFullYear();

  return (
    <div className="max-w-2xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <Link href="/" className="text-xs text-slate-500 hover:text-slate-300 transition-colors">
          ← Back to board
        </Link>
        <div className="mt-4 flex items-end gap-4">
          <div className="h-16 w-16 rounded-2xl bg-slate-800 border border-slate-700 flex items-center justify-center text-2xl font-bold text-slate-300">
            {username[0]?.toUpperCase()}
          </div>
          <div>
            <div className="text-2xl font-bold text-slate-100">{profile.username}</div>
            <div className="text-xs text-slate-500 mt-0.5">Member since {joinedYear}</div>
          </div>
        </div>

        {/* Stats row — filter buttons */}
        <div className="mt-4 flex gap-2 flex-wrap">
          {[
            { key: "all" as const, label: "Votes", count: profile.total_votes, activeStyle: { borderColor: "#94a3b8", backgroundColor: "#1e293b" } },
            { key: "success" as const, label: "✅ Success", count: profile.total_success, activeStyle: { borderColor: "#059669", backgroundColor: "#064e3b66" } },
            { key: "bust" as const, label: "❌ Bust", count: profile.total_bust, activeStyle: { borderColor: "#dc2626", backgroundColor: "#450a0a66" } },
          ].map(({ key, label, count, activeStyle }) => {
            const isActive = voteFilter === key;
            return (
              <button
                key={key}
                type="button"
                onClick={() => changeFilter(key)}
                className="rounded-2xl border px-4 py-3 text-center transition-colors"
                style={isActive ? activeStyle : { borderColor: "#1e293b", backgroundColor: "rgba(15,23,42,0.4)" }}
              >
                <div className="text-xl font-bold text-slate-100">{count}</div>
                <div className="text-[10px] text-slate-500 mt-0.5">{label}</div>
              </button>
            );
          })}
          <button
            type="button"
            onClick={() => setTab("comments")}
            className="rounded-2xl border px-4 py-3 text-center transition-colors"
            style={tab === "comments" ? { borderColor: "#94a3b8", backgroundColor: "#1e293b" } : { borderColor: "#1e293b", backgroundColor: "rgba(15,23,42,0.4)" }}
          >
            <div className="text-xl font-bold text-slate-100">{profile.total_comments}</div>
            <div className="text-[10px] text-slate-500 mt-0.5">Comments</div>
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-slate-800 mb-4">
        {(["votes", "comments"] as const).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm transition-colors ${
              tab === t
                ? "border-b-2 border-slate-200 text-slate-100 -mb-px"
                : "text-slate-500 hover:text-slate-300"
            }`}
          >
            {t === "votes"
              ? `Votes (${profile.total_votes.toLocaleString()})`
              : `Comments (${profile.total_comments.toLocaleString()})`}
          </button>
        ))}
      </div>

      {/* Votes tab */}
      {tab === "votes" && (
        <div className="space-y-2">
          {profile.votes.length === 0 ? (
            <div className="text-sm text-slate-500 py-4">No votes yet.</div>
          ) : (
            <>
              {profile.votes.map((v, i) => (
                <div key={i} className="flex items-center gap-3">
                  <div className="flex-1 min-w-0">
                    <PickCard
                      year={v.year} overall={v.overall} round={v.round}
                      pick_in_round={v.pick_in_round} player_name={v.player_name}
                      team_abbrev={v.team_abbrev}
                    />
                  </div>
                  <VoteChip value={v.value} />
                </div>
              ))}
              <Pager
                offset={votesOffset}
                total={voteFilter === "success" ? profile.total_success : voteFilter === "bust" ? profile.total_bust : profile.total_votes}
                onPrev={() => setVotesOffset(o => Math.max(0, o - PAGE_SIZE))}
                onNext={() => setVotesOffset(o => o + PAGE_SIZE)}
              />
            </>
          )}
        </div>
      )}

      {/* Comments tab */}
      {tab === "comments" && (
        <div className="space-y-3">
          {profile.comments.length === 0 ? (
            <div className="text-sm text-slate-500 py-4">No comments yet.</div>
          ) : (
            <>
              {profile.comments.map((c) => (
                <div key={c.id} className="rounded-2xl border border-slate-800 bg-slate-900/30 p-4">
                  <PickCard
                    year={c.year} overall={c.overall} round={c.round}
                    pick_in_round={c.pick_in_round} player_name={c.player_name}
                    team_abbrev={c.team_abbrev}
                  />
                  <div className="mt-3 text-sm text-slate-200 whitespace-pre-wrap">{c.body}</div>
                  <div className="mt-2 text-[10px] text-slate-600">
                    {new Date(c.created_at).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })}
                  </div>
                </div>
              ))}
              <Pager
                offset={commentsOffset}
                total={profile.total_comments}
                onPrev={() => setCommentsOffset(o => Math.max(0, o - PAGE_SIZE))}
                onNext={() => setCommentsOffset(o => o + PAGE_SIZE)}
              />
            </>
          )}
        </div>
      )}
    </div>
  );
}
