import type { Metadata } from "next";
import DraftBoardPage from "../ui/draft-board-page";

export const metadata: Metadata = {
  title: "Rough Draft",
  description:
    "Vote on every NFL draft pick since 2000. Hit or bust, decided by the community.",
};

export default function Page() {
  return <DraftBoardPage />;
}
