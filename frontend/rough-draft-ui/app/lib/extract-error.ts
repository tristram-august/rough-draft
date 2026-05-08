export function extractError(data: any, fallback: string): string {
  if (!data?.detail) return fallback;
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail)) {
    return data.detail.map((e: any) => {
      const raw: string = e.msg ?? String(e);
      const field = Array.isArray(e.loc) ? String(e.loc[e.loc.length - 1]) : null;
      const label = field ? field.charAt(0).toUpperCase() + field.slice(1) : null;
      return label ? raw.replace(/^String\b/, label) : raw;
    }).join("; ");
  }
  return fallback;
}
