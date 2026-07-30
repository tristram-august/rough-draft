import type { Metadata } from "next";
import PicksPage from "../ui/picks-page";

export const metadata: Metadata = {
  title: "Picks",
  description:
    "Pick every NFL game straight up and track your record against everyone else, week by week.",
};

export default function Page() {
  return <PicksPage />;
}
