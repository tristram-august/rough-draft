import { getJson } from "./fantasy";

export type TeamStatSort =
  | "team"
  | "off_epa"
  | "off_epa_per_play"
  | "points_for"
  | "pass_yards"
  | "pass_tds"
  | "rush_yards"
  | "rush_tds"
  | "giveaways"
  | "def_epa_allowed"
  | "def_epa_per_play_allowed"
  | "points_against"
  | "def_sacks"
  | "def_interceptions"
  | "takeaways"
  | "turnover_margin";

export type SortDirection = "asc" | "desc";

export type TeamStatRow = {
  team: string;
  team_name: string | null;
  games: number;
  off_plays: number;
  off_epa: number;
  off_epa_per_play: number | null;
  points_for: number;
  pass_yards: number;
  pass_tds: number;
  rush_yards: number;
  rush_tds: number;
  giveaways: number;
  def_plays_faced: number;
  def_epa_allowed: number;
  def_epa_per_play_allowed: number | null;
  points_against: number;
  def_sacks: number;
  def_interceptions: number;
  takeaways: number;
  turnover_margin: number;
};

export type TeamStats = {
  season: number;
  week: number | null;
  season_type: string;
  total: number;
  rows: TeamStatRow[];
};

export function fetchTeamSeasons() {
  return getJson<number[]>("/teams/seasons");
}

export function fetchTeamWeeks(season: number) {
  return getJson<number[]>(`/teams/weeks?season=${season}`);
}

export function fetchTeamStats(params: {
  season: number;
  week?: number | null;
  sort?: TeamStatSort;
  direction?: SortDirection;
}) {
  const q = new URLSearchParams({
    season: String(params.season),
    sort: params.sort ?? "off_epa_per_play",
    direction: params.direction ?? "desc",
  });
  if (params.week != null) q.set("week", String(params.week));
  return getJson<TeamStats>(`/teams/stats?${q}`);
}
