import { API_BASE } from "./posts";

export type Scoring = "ppr" | "half" | "std";
export type FantasyPosition = "ALL" | "QB" | "RB" | "WR" | "TE" | "FLEX";
export type FantasySort =
  | "total"
  | "ppg"
  | "games"
  | "name"
  | "td"
  | "pass_yards"
  | "pass_tds"
  | "pass_ints"
  | "rush_yards"
  | "rush_tds"
  | "receptions"
  | "rec_yards"
  | "rec_tds";

export type SortDirection = "asc" | "desc";

export const SCORING_LABELS: Record<Scoring, string> = {
  ppr: "PPR",
  half: "Half",
  std: "Standard",
};

export const POSITIONS: FantasyPosition[] = ["ALL", "QB", "RB", "WR", "TE", "FLEX"];

export type FantasyStatLine = {
  pass_yards: number;
  pass_tds: number;
  pass_ints: number;
  rush_yards: number;
  rush_tds: number;
  receptions: number;
  rec_yards: number;
  rec_tds: number;
  fumbles_lost: number;
};

export type FantasyLeaderRow = {
  rank: number;
  gsis_id: string;
  name: string;
  position: string | null;
  team: string | null;
  headshot: string | null;
  games: number;
  fantasy_points: number;
  points_per_game: number;
  stats: FantasyStatLine;
};

export type FantasyLeaderboard = {
  season: number;
  week: number | null;
  season_type: string;
  scoring: Scoring;
  position: FantasyPosition;
  sort: FantasySort;
  direction: SortDirection;
  total: number;
  rows: FantasyLeaderRow[];
};

export type FantasyGameRow = {
  season: number;
  week: number | null;
  season_type: string | null;
  team: string | null;
  opponent: string | null;
  fantasy_points: number;
  stats: FantasyStatLine;
};

export type FantasyPlayerSeason = {
  season: number;
  team: string | null;
  games: number;
  fantasy_points: number;
  points_per_game: number;
  stats: FantasyStatLine;
};

export type FantasyPlayer = {
  gsis_id: string;
  name: string;
  position: string | null;
  headshot: string | null;
  scoring: Scoring;
  seasons: FantasyPlayerSeason[];
  games: FantasyGameRow[];
};

// ── Preseason draft board (ECR/ADP) ──────────────────────────────────────────

export type FantasyBoardRow = {
  overall_rank: number;
  tier: number | null;
  player_name: string;
  team: string | null;
  position: string;
  position_rank: number | null;
  bye_week: number | null;
  sos: number | null;
  ecr_vs_adp: number | null;
  avg_diff: number | null;
  gsis_id: string | null;
};

export type FantasyBoard = {
  season: number;
  total: number;
  positions: string[];
  rows: FantasyBoardRow[];
};

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return res.json();
}

export function fetchFantasySeasons() {
  return getJson<number[]>("/fantasy/seasons");
}

export function fetchFantasyWeeks(season: number) {
  return getJson<number[]>(`/fantasy/weeks?season=${season}`);
}

export function fetchLeaderboard(params: {
  season: number;
  week?: number | null;
  position: FantasyPosition;
  scoring: Scoring;
  sort: FantasySort;
  direction?: SortDirection;
  minGames?: number;
  limit?: number;
}) {
  const q = new URLSearchParams({
    season: String(params.season),
    position: params.position,
    scoring: params.scoring,
    sort: params.sort,
    direction: params.direction ?? "desc",
    limit: String(params.limit ?? 100),
  });
  if (params.week != null) q.set("week", String(params.week));
  if (params.minGames && params.minGames > 1) q.set("min_games", String(params.minGames));
  return getJson<FantasyLeaderboard>(`/fantasy/leaderboard?${q}`);
}

/** Seasons that have a preseason draft board loaded (vs. production rankings). */
export function fetchBoardSeasons() {
  return getJson<number[]>("/fantasy/board/seasons");
}

export function fetchBoard(season: number, position = "ALL", limit = 300) {
  const q = new URLSearchParams({
    season: String(season),
    position,
    limit: String(limit),
  });
  return getJson<FantasyBoard>(`/fantasy/board?${q}`);
}

export function fetchFantasyPlayer(gsisId: string, scoring: Scoring, season?: number | null) {
  const q = new URLSearchParams({ scoring });
  if (season != null) q.set("season", String(season));
  return getJson<FantasyPlayer>(`/fantasy/player/${encodeURIComponent(gsisId)}?${q}`);
}
