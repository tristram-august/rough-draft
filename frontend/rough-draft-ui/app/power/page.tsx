import type { Metadata } from "next";
import PowerRankingsPage from "../ui/power-rankings-page";

export const metadata: Metadata = {
  title: "Power Rankings",
  description:
    "NFL team power rankings 1-32 and positional rankings, with community consensus and week-over-week movement.",
};

export default function Page() {
  return <PowerRankingsPage />;
}
