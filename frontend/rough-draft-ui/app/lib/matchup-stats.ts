import { API_BASE } from "./posts";

export type MatchupStatRow = {
  stat_label: string;
  team: string;
  team_value: string;
  team_rank: number | null;
  opp_team: string;
  opp_stat_label: string;
  opp_value: string;
  opp_rank: number | null;
  team_favored: boolean | null;
};

export type MatchupStatCategory = {
  category: string;
  rows: MatchupStatRow[];
};

export type MatchupStats = {
  game_id: string;
  source_season: number | null;
  categories: MatchupStatCategory[];
};

export async function fetchMatchupStats(gameId: string): Promise<MatchupStats> {
  const res = await fetch(`${API_BASE}/matchup-stats/${encodeURIComponent(gameId)}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Failed to load matchup stats (${res.status})`);
  return res.json();
}
