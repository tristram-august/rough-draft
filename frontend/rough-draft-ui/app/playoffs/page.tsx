import type { Metadata } from "next";
import { PlayoffsPage } from "../ui/playoffs-page";

export const metadata: Metadata = {
  title: "Playoff Odds",
  description: "Every NFL team's chance to make the playoffs, win its division and win the Super Bowl, updated weekly from 10,000 simulated seasons.",
};

export default function Page() {
  return <PlayoffsPage />;
}
