import type { Metadata } from "next";
import PicksPage from "../ui/picks-page";

export const metadata: Metadata = {
  title: "Schedule",
  description: "This week's NFL games with kickoff times, betting lines, Elo model favorites and matchup breakdowns.",
};

export default function Page() {
  return <PicksPage />;
}
