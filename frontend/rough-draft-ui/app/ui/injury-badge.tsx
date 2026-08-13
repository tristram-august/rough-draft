import type { InjuryRow } from "../lib/injuries";

const SEVERE = new Set(["OUT", "IR", "COV-IR", "SUSPENDED", "PUP"]);
const CAUTION = new Set(["QUESTIONABLE", "DOUBTFUL", "NOT STARTING"]);

export function InjuryBadge({ injury }: { injury: InjuryRow | null | undefined }) {
  if (!injury) return null;

  const status = injury.status.toUpperCase();
  const severe = SEVERE.has(status);
  const caution = CAUTION.has(status);
  if (!severe && !caution) return null;

  const tooltip = [injury.status, injury.injury_type, injury.comment].filter(Boolean).join(" — ");

  return (
    <span
      title={tooltip || undefined}
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${
        severe
          ? "border-rose-700/50 bg-rose-950/30 text-rose-400"
          : "border-amber-700/50 bg-amber-950/30 text-amber-400"
      }`}
    >
      {injury.status}
    </span>
  );
}
