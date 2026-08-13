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

export function fetchCompare(ids: number[]) {
  const q = new URLSearchParams({ ids: ids.join(",") });
  return getJson<ComparePlayersResult>(`/players/compare?${q}`);
}
