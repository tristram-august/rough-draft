import { API_BASE } from "./posts";

export type PowerSubjectType = "team" | "player";

export type PowerSubject = {
  subject_id: string;
  name: string;
  subtitle: string | null;
  image: string | null;
};

export type PowerEntry = {
  rank: number;
  subject_id: string;
  name: string;
  subtitle: string | null;
  image: string | null;
  note: string | null;
  previous_rank: number | null;
  movement: number | null;
  consensus_rank: number | null;
  consensus_ballots: number;
  your_rank: number | null;
};

export type PowerRanking = {
  subject_type: PowerSubjectType;
  subject_group: string;
  season: number;
  week: number | null;
  has_official: boolean;
  author_username: string | null;
  updated_at: string | null;
  ballot_count: number;
  entries: PowerEntry[];
};

export type PowerScope = {
  subject_type: PowerSubjectType;
  subject_group: string;
  season: number;
  week: number | null;
};

function scopeParams(scope: PowerScope): URLSearchParams {
  const q = new URLSearchParams({
    subject_type: scope.subject_type,
    subject_group: scope.subject_group,
    season: String(scope.season),
  });
  if (scope.week != null) q.set("week", String(scope.week));
  return q;
}

async function getJson<T>(path: string, token?: string | null): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    cache: "no-store",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return res.json();
}

export function fetchPowerSubjects(scope: PowerScope) {
  return getJson<PowerSubject[]>(`/power/subjects?${scopeParams(scope)}`);
}

export function fetchPowerRanking(scope: PowerScope, token?: string | null) {
  return getJson<PowerRanking>(`/power/rankings?${scopeParams(scope)}`, token);
}

export function fetchMyBallot(scope: PowerScope, official: boolean, token: string) {
  const q = scopeParams(scope);
  if (official) q.set("official", "true");
  return getJson<string[]>(`/power/mine?${q}`, token);
}

export async function saveBallot(
  scope: PowerScope,
  subjectIds: string[],
  official: boolean,
  token: string
): Promise<PowerRanking> {
  const q = scopeParams(scope);
  if (official) q.set("official", "true");

  const res = await fetch(`${API_BASE}/power/mine?${q}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ subject_ids: subjectIds, notes: {} }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data?.detail ?? `Couldn't save the ranking (${res.status})`);
  }
  return res.json();
}
