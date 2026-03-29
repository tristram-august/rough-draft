export function getClientId(): string {
  if (typeof window === "undefined") return "server";

  const key = "roughDraftClientId";
  const existing = window.localStorage.getItem(key);
  if (existing && existing.length >= 8) return existing;

  const id =
    globalThis.crypto?.randomUUID?.() ??
    `rd_${Math.random().toString(16).slice(2)}_${Date.now().toString(16)}`;

  window.localStorage.setItem(key, id);
  return id;
}