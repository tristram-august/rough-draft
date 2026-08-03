/** Primary brand color per team, used consistently across the draft board, profile, and picks. */
export const TEAM_COLORS: Record<string, string> = {
  ARI: "#97233F", ATL: "#A71930", BAL: "#241773", BUF: "#00338D",
  CAR: "#0085CA", CHI: "#C83803", CIN: "#FB4F14", CLE: "#FF3C00",
  DAL: "#003594", DEN: "#FB4F14", DET: "#0076B6", GB:  "#203731",
  HOU: "#C60C30", IND: "#002C5F", JAX: "#006778", KC:  "#E31837",
  LAC: "#0080C6", LAR: "#003594", LV:  "#A5ACAF", MIA: "#008E97",
  MIN: "#4F2683", NE:  "#002244", NO:  "#9F8958", NYG: "#0B2265",
  NYJ: "#125740", PHI: "#004C54", PIT: "#FFB612", SEA: "#69BE28",
  SF:  "#AA0000", TB:  "#D50A0A", TEN: "#4B92DB", WAS: "#5A1414",
  // Historical (relocated teams)
  SD:  "#0080C6", STL: "#003594", OAK: "#A5ACAF",
};

export function teamColor(abbrev: string | null | undefined): string {
  return TEAM_COLORS[abbrev?.toUpperCase() ?? ""] ?? "#475569";
}
