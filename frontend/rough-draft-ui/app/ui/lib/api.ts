import { getClientId } from "./clientId";

export async function apiFetch(input: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  headers.set("X-Client-Id", getClientId());

  // Only set JSON content-type when we actually send a body.
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(input, { ...init, headers, cache: "no-store" });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}${text ? ` — ${text}` : ""}`);
  }
  return res;
}