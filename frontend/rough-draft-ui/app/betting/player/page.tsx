import type { Metadata } from "next";
import ReceivingPropPage from "../../ui/receiving-prop-page";
import { STAT_OPTIONS, type StatKey } from "../../lib/betting";

export const metadata: Metadata = {
  title: "Player Prop Detail",
  description: "One player's prop probabilities, game log and matchup context.",
  robots: { index: false, follow: false },
};

export default async function Page({
  searchParams,
}: {
  searchParams: Promise<{ gsis_id?: string; stat?: string; line?: string }>;
}) {
  const { gsis_id, stat, line } = await searchParams;
  const validStat = STAT_OPTIONS.some((o) => o.key === stat) ? (stat as StatKey) : "rec_yards";
  const parsedLine = line && /^\d{1,3}$/.test(line) ? Number(line) : null;
  return <ReceivingPropPage initialPlayer={gsis_id ?? null} initialStat={validStat} initialLine={parsedLine} />;
}
