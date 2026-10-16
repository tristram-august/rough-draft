import type { Metadata } from "next";
import { TeamProfilePage } from "../../ui/team-profile-page";

export async function generateMetadata({ params }: { params: Promise<{ team: string }> }): Promise<Metadata> {
  const { team } = await params;
  return {
    title: `${team.toUpperCase()} Team Profile`,
    description: "Season profile for one NFL team: game log, offense, defense and special teams, ranked against the league.",
  };
}

export default async function Page({
  params,
  searchParams,
}: {
  params: Promise<{ team: string }>;
  searchParams: Promise<{ season?: string }>;
}) {
  const { team } = await params;
  const { season } = await searchParams;
  const parsedSeason = season && /^\d{4}$/.test(season) ? Number(season) : null;
  return <TeamProfilePage team={team.toUpperCase()} initialSeason={parsedSeason} />;
}
