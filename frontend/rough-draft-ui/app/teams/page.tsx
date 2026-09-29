import type { Metadata } from "next";
import { TeamStatsPage } from "../ui/team-stats-page";

export const metadata: Metadata = {
  title: "Team Stats",
  description: "NFL team offensive and defensive stats by season and week, including EPA/play.",
};

export default function Page() {
  return <TeamStatsPage />;
}
