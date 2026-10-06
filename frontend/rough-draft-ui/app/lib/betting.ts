import { getJson } from "./fantasy";

export type StatKey =
  | "rec_yards"
  | "receptions"
  | "rec_tds"
  | "pass_attempts"
  | "pass_yards"
  | "pass_tds"
  | "interceptions"
  | "rush_attempts"
  | "rush_yards"
  | "rush_tds";

export type StatGroup = "receiving" | "passing" | "rushing";

export type StatOption = {
  key: StatKey;
  label: string;
  unit: string;
  group: StatGroup;
  note?: string;
};

export const STAT_OPTIONS: StatOption[] = [
  { key: "rec_yards", label: "Receiving yards", unit: "yds", group: "receiving" },
  { key: "receptions", label: "Receptions", unit: "rec", group: "receiving" },
  {
    key: "rec_tds",
    label: "Receiving TDs",
    unit: "TD",
    group: "receiving",
  },
  { key: "pass_attempts", label: "Pass attempts", unit: "att", group: "passing" },
  { key: "pass_yards", label: "Passing yards", unit: "yds", group: "passing" },
  {
    key: "pass_tds",
    label: "Passing TDs",
    unit: "TD",
    group: "passing",
  },
  { key: "interceptions", label: "Interceptions", unit: "INT", group: "passing" },
  { key: "rush_attempts", label: "Rush attempts", unit: "att", group: "rushing" },
  { key: "rush_yards", label: "Rushing yards", unit: "yds", group: "rushing" },
  {
    key: "rush_tds",
    label: "Rushing TDs",
    unit: "TD",
    group: "rushing",
  },
];

export const GROUP_LABELS: Record<StatGroup, string> = {
  receiving: "Receiver",
  passing: "Passer",
  rushing: "Rusher",
};

export const GROUP_NOUN: Record<StatGroup, string> = {
  receiving: "receiver",
  passing: "passer",
  rushing: "rusher",
};

export const GAME_LOG_COLUMNS: Record<StatGroup, { key: string; label: string }[]> = {
  receiving: [
    { key: "targets", label: "Targets" },
    { key: "receptions", label: "Rec" },
    { key: "yards", label: "Yds" },
    { key: "tds", label: "TD" },
  ],
  passing: [
    { key: "attempts", label: "Att" },
    { key: "pass_yards", label: "Yds" },
    { key: "pass_tds", label: "TD" },
    { key: "ints", label: "INT" },
  ],
  rushing: [
    { key: "attempts", label: "Att" },
    { key: "rush_yards", label: "Yds" },
    { key: "rush_tds", label: "TD" },
  ],
};

export type BettingPlayer = {
  gsis_id: string;
  name: string;
  team: string | null;
  position: string | null;
};

export type ReceivingDistributionPoint = { threshold: number; p_over: number };

export type GameLogRow = {
  season: number;
  week: number;
  opponent: string;
  values: Record<string, number>;
};

export type TopAllowedGame = {
  player: string;
  season: number;
  week: number;
  value: number;
};

export type PropContext = {
  opponent: {
    team: string;
    stat: StatKey;
    games: number;
    avg_season: number | null;
    avg_last4: number | null;
    league_avg: number | null;
    top_games: TopAllowedGame[];
  };
  usage: {
    target_share_season: number | null;
    target_share_last4: number | null;
    carry_share_season: number | null;
    carry_share_last4: number | null;
    air_yards_share_season: number | null;
    air_yards_share_last4: number | null;
    volume_per_game_season: number | null;
    volume_per_game_last4: number | null;
  };
  game: {
    total_line: number | null;
    spread_line: number | null;
    implied_team_total: number | null;
    roof: string | null;
  };
};

export type PlayerProp = {
  gsis_id: string;
  name: string;
  position: string | null;
  team: string;
  season: number;
  week: number;
  opponent: string;
  stat: StatKey;
  group: StatGroup;
  line_max: number;
  mean: number;
  games_used: number;
  thin_sample: boolean;
  distribution: ReceivingDistributionPoint[];
  game_log: GameLogRow[];
  context: PropContext;
  disclaimer: string;
};

export type CalibrationBucket = { predicted: number; actual: number; n: number };

export type Calibration = {
  stat: StatKey;
  first_season: number;
  last_season: number;
  predictions: number;
  brier_model: number | null;
  brier_baseline: number | null;
  buckets: CalibrationBucket[];
};

export type UpcomingWeek = { season: number; week: number | null };

export function fetchUpcomingWeek(season: number) {
  return getJson<UpcomingWeek>(`/betting/upcoming-week?season=${season}`);
}

export function fetchBettingPlayers(season: number, group: StatGroup) {
  const path = { receiving: "receivers", passing: "passers", rushing: "rushers" }[group];
  return getJson<BettingPlayer[]>(`/betting/${path}?season=${season}`);
}

export function fetchCalibration(season: number, stat: StatKey) {
  return getJson<Calibration>(`/betting/calibration?season=${season}&stat=${stat}`);
}

export function fetchPlayerProp(gsisId: string, season: number, week: number, stat: StatKey) {
  const q = new URLSearchParams({
    gsis_id: gsisId,
    season: String(season),
    week: String(week),
    stat,
  });
  return getJson<PlayerProp>(`/betting/receiving-prop?${q}`);
}
