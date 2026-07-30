import type { Metadata } from "next";
import FantasyRankingsPage from "../ui/fantasy-rankings-page";
import { fetchBoardSeasons, fetchFantasySeasons } from "../lib/fantasy";

export const metadata: Metadata = {
  title: "Fantasy Draft",
  description:
    "Preseason fantasy draft board with tiers and ADP, plus historical fantasy production rankings in PPR, half PPR, or standard scoring.",
};

export const dynamic = "force-dynamic";

export default async function Page() {
  // Resolved on the server so the first paint already knows whether this season
  // is a draft board or production rankings — otherwise the heading flips.
  const [boardSeasons, productionSeasons] = await Promise.all([
    fetchBoardSeasons().catch(() => [] as number[]),
    fetchFantasySeasons().catch(() => [] as number[]),
  ]);

  return (
    <FantasyRankingsPage
      initialBoardSeasons={boardSeasons}
      initialProductionSeasons={productionSeasons}
    />
  );
}
