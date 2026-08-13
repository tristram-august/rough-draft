import { getJson } from "./fantasy";

export type InjuryRow = {
  gsis_id: string;
  player_name: string;
  team: string | null;
  position: string | null;
  status: string;
  status_short: string | null;
  injury_type: string | null;
  comment: string | null;
  probability_of_playing: string | null;
  updated_at: string;
};

export function fetchInjuries() {
  return getJson<InjuryRow[]>("/injuries");
}
