import { getJson, type Scoring } from "./fantasy";

export type PlayerProjectionRow = {
  gsis_id: string | null;
  player_name: string;
  team: string | null;
  position: string;
  points: number | null;
  points_ppr: number | null;
  points_half: number | null;
  stats: Record<string, number> | null;
};

export type PlayerProjections = {
  season: number;
  week: number | null;
  is_ros: boolean;
  total: number;
  rows: PlayerProjectionRow[];
};

export function fetchProjectionWeeks(season: number) {
  return getJson<number[]>(`/fantasy/projections/weeks?season=${season}`);
}

export function fetchProjections(params: {
  season: number;
  week?: number | null;
  ros?: boolean;
  position?: string;
  scoring?: Scoring;
  limit?: number;
  offset?: number;
}) {
  const q = new URLSearchParams({
    season: String(params.season),
    position: params.position ?? "ALL",
    scoring: params.scoring ?? "ppr",
    limit: String(params.limit ?? 300),
    offset: String(params.offset ?? 0),
  });
  if (params.ros) {
    q.set("ros", "true");
  } else if (params.week != null) {
    q.set("week", String(params.week));
  }
  return getJson<PlayerProjections>(`/fantasy/projections?${q}`);
}
