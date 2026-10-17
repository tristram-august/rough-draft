import type { Metadata } from "next";
import { PropBoardPage } from "../ui/prop-board-page";

export const metadata: Metadata = {
  title: "Prop Board",
  description: "Every player prop for the week with model odds, hit rates and matchups.",
  robots: { index: false, follow: false },
};

export default function Page() {
  return <PropBoardPage />;
}
