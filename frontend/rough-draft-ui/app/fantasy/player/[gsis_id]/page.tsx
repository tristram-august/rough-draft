import type { Metadata } from "next";
import FantasyPlayerPage from "../../../ui/fantasy-player-page";
import type { Scoring } from "../../../lib/fantasy";

export const metadata: Metadata = {
  title: "Fantasy Player",
};

const SCORINGS: Scoring[] = ["ppr", "half", "std"];

export default async function Page({
  params,
  searchParams,
}: {
  params: Promise<{ gsis_id: string }>;
  searchParams: Promise<{ season?: string; scoring?: string }>;
}) {
  const { gsis_id } = await params;
  const { season, scoring } = await searchParams;

  const parsedSeason = season && /^\d{4}$/.test(season) ? Number(season) : null;
  const parsedScoring = SCORINGS.includes(scoring as Scoring) ? (scoring as Scoring) : "ppr";

  return (
    <FantasyPlayerPage
      gsisId={gsis_id}
      initialSeason={parsedSeason}
      initialScoring={parsedScoring}
    />
  );
}
