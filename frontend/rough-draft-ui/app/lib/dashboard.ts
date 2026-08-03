import { API_BASE } from "./posts";

export type Game = {
  game_id: string;
  season: number;
  game_type: string | null;
  week: number | null;
  gameday: string | null;
  weekday: string | null;
  gametime: string | null;
  kickoff_et: string | null;
  away_team: string;
  home_team: string;
  away_name: string | null;
  home_name: string | null;
  away_score: number | null;
  home_score: number | null;
  final: boolean;
  spread_line: number | null;
  total_line: number | null;
  div_game: boolean | null;
  stadium: string | null;
};

export type UpcomingSchedule = {
  season: number | null;
  week: number | null;
  game_type: string | null;
  days_until_kickoff: number | null;
  first_kickoff_et: string | null;
  in_season: boolean;
  games: Game[];
};

export type NewsItem = {
  headline: string;
  description: string | null;
  published: string | null;
  url: string | null;
  image: string | null;
};

export type NewsFeed = {
  items: NewsItem[];
  fetched_at: string;
  stale: boolean;
  source: string;
};

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return res.json();
}

export function fetchUpcoming(limit = 16) {
  return getJson<UpcomingSchedule>(`/schedule/upcoming?limit=${limit}`);
}

export function fetchNews(limit = 6) {
  return getJson<NewsFeed>(`/news?limit=${limit}`);
}

/** "1:00 PM" from an ET "13:00". */
export function formatKickoffTime(gametime: string | null): string {
  if (!gametime) return "TBD";
  const [hhRaw, mm] = gametime.split(":");
  const hh = Number(hhRaw);
  if (Number.isNaN(hh)) return gametime;
  const period = hh >= 12 ? "PM" : "AM";
  const hour12 = hh % 12 === 0 ? 12 : hh % 12;
  return `${hour12}:${mm ?? "00"} ${period}`;
}

export function formatGameDay(gameday: string | null): string {
  if (!gameday) return "";
  return new Date(`${gameday}T12:00:00Z`).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
}

/** "SEA -3.5" from a home-perspective spread_line, or "PK" for a pick'em. */
export function spreadLabel(game: {
  spread_line: number | null;
  home_team: string;
  away_team: string;
}): string | null {
  if (game.spread_line == null) return null;
  // nflverse spread_line is from the home team's perspective.
  const favored = game.spread_line > 0 ? game.home_team : game.away_team;
  const magnitude = Math.abs(game.spread_line);
  if (magnitude === 0) return "PK";
  return `${favored} -${magnitude}`;
}

/** Relative age for news items — "3h ago", "2d ago". */
export function timeAgo(iso: string | null): string {
  if (!iso) return "";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const mins = Math.floor((Date.now() - then) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}
