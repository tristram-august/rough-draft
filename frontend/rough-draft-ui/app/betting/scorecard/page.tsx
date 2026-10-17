import type { Metadata } from "next";
import { PropScorecardPage } from "../../ui/prop-scorecard-page";

export const metadata: Metadata = {
  title: "Prop Model Scorecard",
  description: "How the prop board's picks actually did, week by week, against simple baselines.",
  robots: { index: false, follow: false },
};

export default function Page() {
  return <PropScorecardPage />;
}
