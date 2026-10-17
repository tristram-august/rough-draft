import { getJson } from "./fantasy";

export type PlayoffHistoryPoint = {
  week: number;
  make_playoffs: number;
  win_division: number;
  win_super_bowl: number;
};

export type PlayoffTeamOdds = {
  team: string;
  team_name: string | null;
  conference: "AFC" | "NFC" | null;
  division: string | null;
  elo: number;
  wins: number;
  losses: number;
  mean_wins: number;
  make_playoffs: number;
  win_division: number;
  first_seed: number;
  win_conference: number;
  win_super_bowl: number;
  seed_probs: number[];
  history: PlayoffHistoryPoint[];
};

export type PlayoffOdds = {
  season: number;
  week: number;
  weeks: number[];
  sims: number;
  updated_at: string;
  teams: PlayoffTeamOdds[];
};

export type PlayoffCalibration = {
  seasons: string | null;
  rows: { bucket_lo: number; bucket_hi: number; n: number; predicted: number; actual: number }[];
};

export function fetchPlayoffOdds(week?: number | null) {
  return getJson<PlayoffOdds>(`/playoffs/odds${week != null ? `?week=${week}` : ""}`);
}

export function fetchPlayoffCalibration() {
  return getJson<PlayoffCalibration>("/playoffs/calibration");
}

/** 0.9431 -> "94%", with "<1%" / ">99%" at the extremes so a real long shot never reads as 0. */
export function fmtProb(p: number) {
  if (p <= 0) return "—";
  if (p < 0.005) return "<1%";
  if (p >= 0.995 && p < 1) return ">99%";
  return `${Math.round(p * 100)}%`;
}

export function fmtRecord(w: number, l: number) {
  const ties = Math.round((w % 1) * 2);
  const fw = Math.floor(w);
  const fl = Math.floor(l);
  return ties ? `${fw}–${fl}–${ties}` : `${fw}–${fl}`;
}
