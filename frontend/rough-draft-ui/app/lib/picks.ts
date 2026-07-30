import { getClientId } from "../ui/lib/clientId";
import { API_BASE } from "./posts";
import type { Game } from "./dashboard";

export type PickSplit = { away: number; home: number; total: number };

export type SlateGame = Game & {
  locked: boolean;
  your_pick: string | null;
  split: PickSplit;
  winner: string | null;
  your_result: "win" | "loss" | "push" | null;
};

export type Slate = {
  season: number | null;
  week: number | null;
  game_type: string | null;
  games: SlateGame[];
};

export type PickLeaderRow = {
  rank: number;
  display_name: string;
  voter_type: string;
  is_you: boolean;
  wins: number;
  losses: number;
  pushes: number;
  graded: number;
  pct: number;
};

export type PickLeaderboard = {
  season: number;
  week: number | null;
  scope: "week" | "season";
  rows: PickLeaderRow[];
};

/** Identity header — anonymous picks key off the same client id as vote. */
function pickHeaders(token?: string | null): HeadersInit {
  const headers: Record<string, string> = { "X-Client-Id": getClientId() };
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

export async function fetchSlate(
  params: { season?: number | null; week?: number | null; token?: string | null } = {}
): Promise<Slate> {
  const q = new URLSearchParams();
  if (params.season != null) q.set("season", String(params.season));
  if (params.week != null) q.set("week", String(params.week));

  const res = await fetch(`${API_BASE}/picks/slate?${q}`, {
    cache: "no-store",
    headers: pickHeaders(params.token),
  });
  if (!res.ok) throw new Error(`Failed to load the slate (${res.status})`);
  return res.json();
}

export async function submitPick(
  gameId: string,
  pickedTeam: string,
  token?: string | null
): Promise<SlateGame> {
  const res = await fetch(`${API_BASE}/picks/${encodeURIComponent(gameId)}`, {
    method: "PUT",
    headers: { ...pickHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify({ picked_team: pickedTeam }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data?.detail ?? `Couldn't save that pick (${res.status})`);
  }
  return res.json();
}

export async function fetchPickLeaderboard(
  season: number,
  week: number | null,
  token?: string | null
): Promise<PickLeaderboard> {
  const q = new URLSearchParams({ season: String(season) });
  if (week != null) q.set("week", String(week));

  const res = await fetch(`${API_BASE}/picks/leaderboard?${q}`, {
    cache: "no-store",
    headers: pickHeaders(token),
  });
  if (!res.ok) throw new Error(`Failed to load standings (${res.status})`);
  return res.json();
}
