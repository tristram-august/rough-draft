import { getJson } from "./fantasy";

export type CompareExpertRank = { expert_id: string; rank: string };

export type ComparePlayerInfo = {
  player_name: string;
  player_team_id: string | null;
  player_position_id: string | null;
  player_page_url: string | null;
};

export type CompareExpertInfo = {
  expert_name: string | null;
  expert_display_name: string | null;
  expert_source_name: string | null;
  expert_twitter_url: string | null;
};

export type ComparePlayersResult = {
  rankings: Record<string, Record<string, CompareExpertRank[]>>;
  players: Record<string, ComparePlayerInfo>;
  experts: Record<string, CompareExpertInfo>;
};

// FantasyPros' compare API returns rankings scoped to one position --
// position=ALL silently comes back with every ranking empty rather than an
// error, so a real position is required, not just an optional filter.
export function fetchCompare(ids: number[], position: string) {
  const q = new URLSearchParams({ ids: ids.join(","), position });
  return getJson<ComparePlayersResult>(`/players/compare?${q}`);
}
