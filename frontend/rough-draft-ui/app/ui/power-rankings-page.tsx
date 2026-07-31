"use client";

import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "./page-header";
import { Segmented } from "./segmented";
import { useAuth } from "../contexts/auth-context";
import {
  fetchMyBallot,
  fetchPowerRanking,
  fetchPowerSubjects,
  saveBallot,
  type PowerScope,
  type PowerSubject,
  type PowerSubjectType,
} from "../lib/power";

const CURRENT_SEASON = 2026;

type ScopeChoice = { label: string; subject_type: PowerSubjectType; subject_group: string };

const SCOPES: ScopeChoice[] = [
  { label: "Teams", subject_type: "team", subject_group: "" },
  { label: "QB", subject_type: "player", subject_group: "QB" },
  { label: "RB", subject_type: "player", subject_group: "RB" },
  { label: "WR", subject_type: "player", subject_group: "WR" },
  { label: "TE", subject_type: "player", subject_group: "TE" },
];

function MovementArrow({ movement }: { movement: number | null }) {
  if (movement == null) return <span className="text-slate-700">—</span>;
  if (movement === 0) return <span className="text-slate-600">–</span>;
  const up = movement > 0;
  return (
    <span className={up ? "text-emerald-400" : "text-rose-400"}>
      {up ? "▲" : "▼"}
      {Math.abs(movement)}
    </span>
  );
}

/**
 * Editable rank number — the fast path for big jumps (typing "2" beats
 * dragging or clicking ↑ twenty-four times). Only commits on blur/Enter, and
 * re-syncs to the real rank whenever another row's move shifts this one, but
 * not while the field is focused (that would fight the user's typing).
 */
function RankInput({
  rank,
  max,
  label,
  onCommit,
}: {
  rank: number;
  max: number;
  label: string;
  onCommit: (nextRank: number) => void;
}) {
  const [draft, setDraft] = React.useState(String(rank));
  const [focused, setFocused] = React.useState(false);

  React.useEffect(() => {
    if (!focused) setDraft(String(rank));
  }, [rank, focused]);

  function commit() {
    const next = Math.round(Number(draft));
    if (Number.isFinite(next) && next >= 1 && next <= max && next !== rank) {
      onCommit(next);
    } else {
      setDraft(String(rank));
    }
  }

  return (
    <input
      type="number"
      inputMode="numeric"
      min={1}
      max={max}
      aria-label={`Set rank for ${label}`}
      value={draft}
      onFocus={(e) => {
        setFocused(true);
        e.target.select();
      }}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={() => {
        setFocused(false);
        commit();
      }}
      onKeyDown={(e) => {
        if (e.key === "Enter") (e.target as HTMLInputElement).blur();
        if (e.key === "Escape") {
          setDraft(String(rank));
          (e.target as HTMLInputElement).blur();
        }
      }}
      className="w-11 shrink-0 rounded-md border border-slate-800 bg-slate-950/60 px-1 py-1 text-center text-xs font-medium text-slate-200 tabular-nums outline-none transition-colors [appearance:textfield] focus:border-sky-600 [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
    />
  );
}

/** Reorderable list: type a rank to jump, drag on desktop, or nudge with arrows. */
function BallotEditor({
  order,
  subjects,
  onChange,
}: {
  order: string[];
  subjects: Map<string, PowerSubject>;
  onChange: (next: string[]) => void;
}) {
  const [dragIndex, setDragIndex] = React.useState<number | null>(null);

  function move(from: number, to: number) {
    if (to < 0 || to >= order.length || from === to) return;
    const next = [...order];
    const [item] = next.splice(from, 1);
    next.splice(to, 0, item);
    onChange(next);
  }

  return (
    <ol className="space-y-1.5">
      {order.map((id, i) => {
        const subject = subjects.get(id);
        return (
          <li
            key={id}
            draggable
            onDragStart={() => setDragIndex(i)}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              if (dragIndex != null) move(dragIndex, i);
              setDragIndex(null);
            }}
            onDragEnd={() => setDragIndex(null)}
            className={`flex items-center gap-3 rounded-xl border px-3 py-2 transition-colors ${
              dragIndex === i
                ? "border-sky-600 bg-sky-950/30"
                : "border-slate-800 bg-slate-900/40 hover:border-slate-700"
            }`}
          >
            <RankInput
              rank={i + 1}
              max={order.length}
              label={subject?.name ?? id}
              onCommit={(nextRank) => move(i, nextRank - 1)}
            />
            <span className="cursor-grab select-none text-slate-700" aria-hidden>
              ⠿
            </span>
            {subject?.image && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={subject.image}
                alt=""
                className="h-7 w-7 shrink-0 rounded-full border border-slate-800 bg-slate-900 object-cover"
              />
            )}
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-medium text-slate-100">
                {subject?.name ?? id}
              </span>
              {subject?.subtitle && (
                <span className="text-[11px] text-slate-500">{subject.subtitle}</span>
              )}
            </span>
            <span className="flex shrink-0 gap-1">
              <button
                type="button"
                aria-label={`Move ${subject?.name ?? id} up`}
                disabled={i === 0}
                onClick={() => move(i, i - 1)}
                className="rounded-md border border-slate-800 px-1.5 py-0.5 text-xs text-slate-500 transition-colors hover:text-slate-200 disabled:opacity-30"
              >
                ↑
              </button>
              <button
                type="button"
                aria-label={`Move ${subject?.name ?? id} down`}
                disabled={i === order.length - 1}
                onClick={() => move(i, i + 1)}
                className="rounded-md border border-slate-800 px-1.5 py-0.5 text-xs text-slate-500 transition-colors hover:text-slate-200 disabled:opacity-30"
              >
                ↓
              </button>
            </span>
          </li>
        );
      })}
    </ol>
  );
}

export default function PowerRankingsPage() {
  const { user, token } = useAuth();
  const queryClient = useQueryClient();

  const [scopeIndex, setScopeIndex] = React.useState(0);
  const [week, setWeek] = React.useState<number | null>(null);
  const [editing, setEditing] = React.useState(false);
  const [asOfficial, setAsOfficial] = React.useState(false);
  const [order, setOrder] = React.useState<string[]>([]);
  const [error, setError] = React.useState<string | null>(null);

  const choice = SCOPES[scopeIndex];
  const scope: PowerScope = {
    subject_type: choice.subject_type,
    subject_group: choice.subject_group,
    season: CURRENT_SEASON,
    week,
  };
  const scopeKey = [choice.subject_type, choice.subject_group, CURRENT_SEASON, week];

  const subjectsQuery = useQuery({
    queryKey: ["power-subjects", ...scopeKey],
    queryFn: () => fetchPowerSubjects(scope),
  });

  const rankingQuery = useQuery({
    queryKey: ["power-ranking", ...scopeKey, token],
    queryFn: () => fetchPowerRanking(scope, token),
  });

  const subjects = React.useMemo(() => {
    const map = new Map<string, PowerSubject>();
    for (const s of subjectsQuery.data ?? []) map.set(s.subject_id, s);
    return map;
  }, [subjectsQuery.data]);

  const mutation = useMutation({
    mutationFn: () => saveBallot(scope, order, asOfficial, token as string),
    onSuccess: () => {
      setEditing(false);
      setError(null);
      queryClient.invalidateQueries({ queryKey: ["power-ranking"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  async function startEditing(official: boolean) {
    if (!token) return;
    setError(null);
    setAsOfficial(official);
    try {
      const saved = await fetchMyBallot(scope, official, token);
      const all = (subjectsQuery.data ?? []).map((s) => s.subject_id);
      // Seed from the saved ballot, appending anything new that appeared since.
      const seeded = saved.length > 0 ? saved.filter((id) => all.includes(id)) : all;
      setOrder([...seeded, ...all.filter((id) => !seeded.includes(id))]);
      setEditing(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't load your ballot");
    }
  }

  const ranking = rankingQuery.data;
  const entries = ranking?.entries ?? [];

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <PageHeader
        eyebrow="Power Rankings"
        title={choice.subject_type === "team" ? "Team power rankings" : `${choice.subject_group} rankings`}
        subtitle={
          editing
            ? "Type a rank to jump straight there, or drag and use the arrows for small moves."
            : "The site's ranking, with community consensus alongside it."
        }
      >
        <Segmented
          ariaLabel="What to rank"
          value={String(scopeIndex)}
          onChange={(v) => {
            setScopeIndex(Number(v));
            setEditing(false);
          }}
          options={SCOPES.map((s, i) => ({ value: String(i), label: s.label }))}
        />
      </PageHeader>

      <div className="mb-5 flex flex-wrap items-center gap-2">
        <select
          aria-label="Week"
          value={week ?? ""}
          onChange={(e) => {
            setWeek(e.target.value === "" ? null : Number(e.target.value));
            setEditing(false);
          }}
          className="rounded-xl border border-slate-800 bg-slate-900/40 px-3 py-1.5 text-xs font-medium text-slate-300 outline-none transition-colors focus:border-slate-600"
        >
          <option value="">Preseason</option>
          {Array.from({ length: 18 }, (_, i) => i + 1).map((w) => (
            <option key={w} value={w}>
              Week {w}
            </option>
          ))}
        </select>

        {!editing && user && (
          <>
            <button
              type="button"
              onClick={() => startEditing(false)}
              className="rounded-xl border border-slate-600 bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-100 transition-colors hover:bg-slate-700"
            >
              {ranking?.entries.some((e) => e.your_rank != null) ? "Edit my ballot" : "Submit a ballot"}
            </button>
            {user.is_mod && (
              <button
                type="button"
                onClick={() => startEditing(true)}
                className="rounded-xl border border-sky-700 bg-sky-900/40 px-3 py-1.5 text-xs font-medium text-sky-100 transition-colors hover:bg-sky-900/70"
              >
                Edit official
              </button>
            )}
          </>
        )}

        {ranking && ranking.ballot_count > 0 && (
          <span className="text-xs text-slate-600">
            {ranking.ballot_count} ballot{ranking.ballot_count === 1 ? "" : "s"}
          </span>
        )}
      </div>

      {error && (
        <div className="mb-4 rounded-xl border border-red-800/40 bg-red-950/20 px-3 py-2 text-sm text-red-300">
          {error}
        </div>
      )}

      {editing ? (
        <div>
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => mutation.mutate()}
              disabled={mutation.isPending}
              className="rounded-xl border border-sky-700 bg-sky-900/40 px-4 py-2 text-sm font-medium text-sky-100 transition-colors hover:bg-sky-900/70 disabled:opacity-50"
            >
              {mutation.isPending
                ? "Saving…"
                : asOfficial
                  ? "Publish official ranking"
                  : "Save my ballot"}
            </button>
            <button
              type="button"
              onClick={() => setEditing(false)}
              className="rounded-xl border border-slate-800 px-4 py-2 text-sm text-slate-400 transition-colors hover:text-slate-200"
            >
              Cancel
            </button>
            {asOfficial && (
              <span className="text-xs text-sky-500/80">Editing the site&apos;s official list</span>
            )}
          </div>
          <BallotEditor order={order} subjects={subjects} onChange={setOrder} />
        </div>
      ) : (
        <>
          {rankingQuery.isLoading && <p className="text-sm text-slate-500">Loading…</p>}

          {ranking && entries.length === 0 && (
            <div className="rounded-3xl border border-dashed border-slate-800 px-5 py-10 text-center">
              <p className="text-sm text-slate-500">Nothing ranked here yet.</p>
              <p className="mt-1 text-xs text-slate-600">
                {user ? "Publish a ranking to get started." : "Sign in to submit a ballot."}
              </p>
            </div>
          )}

          {entries.length > 0 && (
            <div className="overflow-x-auto rounded-3xl border border-slate-800">
              <table className="w-full sm:min-w-[520px] border-collapse text-sm">
                <thead className="bg-slate-900/60">
                  <tr className="text-xs uppercase tracking-wide text-slate-500">
                    <th className="px-3 py-2.5 text-left font-semibold">#</th>
                    <th className="px-2 py-2.5 text-left font-semibold">Mv</th>
                    <th className="px-3 py-2.5 text-left font-semibold">
                      {choice.subject_type === "team" ? "Team" : "Player"}
                    </th>
                    <th className="px-3 py-2.5 text-right font-semibold">Consensus</th>
                    <th className="px-3 py-2.5 text-right font-semibold">You</th>
                  </tr>
                </thead>
                <tbody>
                  {entries.map((e) => (
                    <tr
                      key={e.subject_id}
                      className="border-t border-slate-800/60 transition-colors hover:bg-slate-900/40"
                    >
                      <td className="px-3 py-2 text-sm font-semibold text-slate-100 tabular-nums">
                        {e.rank}
                      </td>
                      <td className="px-2 py-2 text-xs tabular-nums">
                        <MovementArrow movement={e.movement} />
                      </td>
                      <td className="px-3 py-2">
                        <span className="flex items-center gap-2">
                          {e.image && (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img
                              src={e.image}
                              alt=""
                              className="h-7 w-7 shrink-0 rounded-full border border-slate-800 bg-slate-900 object-cover"
                            />
                          )}
                          <span className="min-w-0">
                            <span className="block truncate font-medium text-slate-100">
                              {e.name}
                            </span>
                            {e.subtitle && (
                              <span className="text-[11px] text-slate-500">{e.subtitle}</span>
                            )}
                          </span>
                        </span>
                      </td>
                      <td className="px-3 py-2 text-right text-sm text-slate-400 tabular-nums">
                        {e.consensus_rank != null ? e.consensus_rank.toFixed(1) : "—"}
                      </td>
                      <td className="px-3 py-2 text-right text-sm tabular-nums">
                        {e.your_rank != null ? (
                          <span className="text-sky-400">{e.your_rank}</span>
                        ) : (
                          <span className="text-slate-700">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {ranking?.has_official && ranking.author_username && (
            <p className="mt-3 text-xs text-slate-600">
              Official ranking by {ranking.author_username}
              {ranking.ballot_count > 0 &&
                ` · consensus from ${ranking.ballot_count} community ballot${
                  ranking.ballot_count === 1 ? "" : "s"
                }`}
            </p>
          )}
        </>
      )}
    </div>
  );
}
