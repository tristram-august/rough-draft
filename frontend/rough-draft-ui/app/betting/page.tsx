import type { Metadata } from "next";
import ReceivingPropPage from "../ui/receiving-prop-page";

export const metadata: Metadata = {
  title: "Player Props",
  description: "Receiving-yards probabilities built from game-by-game history and opponent defense.",
  robots: { index: false, follow: false },
};

export default function Page() {
  return <ReceivingPropPage />;
}
