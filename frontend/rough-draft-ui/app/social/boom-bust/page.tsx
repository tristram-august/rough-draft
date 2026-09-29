"use client";

import * as React from "react";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google";
import {
  fetchFantasySeasons,
  fetchProjectionDiff,
  SCORING_LABELS,
  type ProjectionDiffRow,
  type Scoring,
} from "../../lib/fantasy";

const plexSans = IBM_Plex_Sans({ subsets: ["latin"], weight: ["400", "500", "600", "700"], variable: "--font-sans" });
const plexMono = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400", "500", "600", "700"], variable: "--font-mono" });

const ROWS_PER_SLIDE = 6;

const POSITION_COLORS: Record<string, { bg: string; fg: string }> = {
  QB: { bg: "#3a2440", fg: "#d89ff0" },
  RB: { bg: "#123326", fg: "#4fe0a0" },
  WR: { bg: "#122f3a", fg: "#5cc3ef" },
  TE: { bg: "#3a2c14", fg: "#f0b95c" },
  K: { bg: "#1e232b", fg: "#9aa5b4" },
  DST: { bg: "#2c1f3a", fg: "#c79ff5" },
};

type Slide = "cover" | "over" | "under" | "spotlight" | "cta";

function useSlideParams() {
  const params = useSearchParams();
  const week = Number(params.get("week") ?? "0") || null;
  const seasonParam = params.get("season");
  const scoring = (params.get("scoring") as Scoring | null) ?? "ppr";
  const slide = (params.get("slide") as Slide | null) ?? "cover";
  const page = Number(params.get("page") ?? "1") || 1;
  const spotlightId = params.get("spotlight");
  return { week, season: seasonParam ? Number(seasonParam) : null, scoring, slide, page, spotlightId };
}

function fmtDiff(n: number) {
  const s = n.toFixed(1);
  return n > 0 ? `+${s}` : s;
}

function Frame({ children }: { children: React.ReactNode }) {
  return (
    <div
      className={`${plexSans.variable} ${plexMono.variable}`}
      data-slide-ready="true"
      style={{
        width: 1080,
        height: 1350,
        background: "#0d1117",
        color: "#e6e8eb",
        fontFamily: "var(--font-sans), sans-serif",
        display: "flex",
        flexDirection: "column",
        padding: "72px 76px",
        boxSizing: "border-box",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {children}
    </div>
  );
}

function BrandBar({ week, scoring }: { week: number; scoring: Scoring }) {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
      <div style={{ fontFamily: "var(--font-mono), monospace", fontSize: 22, letterSpacing: "0.14em", color: "#e8a33d", fontWeight: 600 }}>
        ROUGH DRAFT FOOTBALL
      </div>
      <div style={{ fontFamily: "var(--font-mono), monospace", fontSize: 20, color: "#5f6b7d" }}>
        WEEK {week} &middot; {SCORING_LABELS[scoring].toUpperCase()}
      </div>
    </div>
  );
}

function FooterBar() {
  return (
    <div
      style={{
        position: "absolute",
        left: 76,
        right: 76,
        bottom: 56,
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        fontFamily: "var(--font-mono), monospace",
        fontSize: 18,
        color: "#5f6b7d",
      }}
    >
      <span>roughdraftfootball.com</span>
      <span>Projections: FantasyPros</span>
    </div>
  );
}

function PositionBadge({ position }: { position: string }) {
  const c = POSITION_COLORS[position] ?? { bg: "#1e232b", fg: "#9aa5b4" };
  return (
    <span
      style={{
        display: "inline-block",
        fontSize: 17,
        fontWeight: 700,
        letterSpacing: "0.03em",
        padding: "3px 9px",
        borderRadius: 6,
        background: c.bg,
        color: c.fg,
        marginRight: 14,
      }}
    >
      {position}
    </span>
  );
}

function CoverSlide({ week, scoring, top }: { week: number; scoring: Scoring; top: ProjectionDiffRow | undefined }) {
  return (
    <Frame>
      <BrandBar week={week} scoring={scoring} />
      <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center" }}>
        <div style={{ fontFamily: "var(--font-mono), monospace", fontSize: 24, letterSpacing: "0.1em", color: "#e8a33d", marginBottom: 18 }}>
          BOOM &amp; BUST
        </div>
        <div style={{ fontSize: 92, fontWeight: 700, lineHeight: 1.03, letterSpacing: "-0.01em" }}>
          Week {week}<br />Boom &amp; Bust
        </div>
        {top && (
          <div
            style={{
              marginTop: 56,
              padding: "28px 32px",
              borderRadius: 20,
              background: "#141a22",
              border: "1px solid #262e39",
            }}
          >
            <div style={{ fontSize: 20, color: "#93a0b3", marginBottom: 10 }}>Biggest beat of the week</div>
            <div style={{ fontSize: 34, fontWeight: 600 }}>
              <PositionBadge position={top.position} />
              {top.name}
            </div>
            <div style={{ marginTop: 10, fontFamily: "var(--font-mono), monospace", fontSize: 26, color: "#93a0b3" }}>
              proj {top.projected.toFixed(1)} &rarr; act {top.actual.toFixed(1)}{" "}
              <span style={{ color: "#3fdb9a", fontWeight: 700 }}>({fmtDiff(top.diff)})</span>
            </div>
          </div>
        )}
      </div>
      <FooterBar />
    </Frame>
  );
}

function ListSlide({
  week,
  scoring,
  kind,
  rows,
  page,
}: {
  week: number;
  scoring: Scoring;
  kind: "over" | "under";
  rows: ProjectionDiffRow[];
  page: number;
}) {
  const isOver = kind === "over";
  const maxAbs = Math.max(1, ...rows.map((r) => Math.abs(r.diff)));
  return (
    <Frame>
      <BrandBar week={week} scoring={scoring} />
      <div style={{ marginTop: 36, display: "flex", alignItems: "baseline", gap: 14 }}>
        <div
          style={{
            width: 14,
            height: 14,
            borderRadius: "50%",
            background: isOver ? "#3fdb9a" : "#f27587",
            transform: "translateY(-2px)",
          }}
        />
        <div style={{ fontSize: 52, fontWeight: 700 }}>{isOver ? "Outperformed" : "Underperformed"}</div>
        {page > 1 && <div style={{ fontFamily: "var(--font-mono), monospace", fontSize: 24, color: "#5f6b7d" }}>cont'd</div>}
      </div>

      <div style={{ marginTop: 30, display: "flex", flexDirection: "column", gap: 10, flex: 1 }}>
        {rows.map((r, i) => {
          const pct = Math.round((Math.abs(r.diff) / maxAbs) * 100);
          const rank = (page - 1) * ROWS_PER_SLIDE + i + 1;
          return (
            <div
              key={r.gsis_id}
              style={{
                display: "grid",
                gridTemplateColumns: "48px 1fr auto",
                alignItems: "center",
                gap: 20,
                padding: "16px 20px",
                borderRadius: 14,
                background: "#141a22",
                border: "1px solid #1e2530",
              }}
            >
              <div style={{ fontFamily: "var(--font-mono), monospace", fontSize: 22, color: "#5f6b7d", textAlign: "right" }}>
                {rank}
              </div>
              <div style={{ minWidth: 0 }}>
                <div style={{ fontSize: 30, fontWeight: 600, display: "flex", alignItems: "center" }}>
                  <PositionBadge position={r.position} />
                  {r.name}
                </div>
                <div style={{ fontSize: 20, color: "#5f6b7d", marginTop: 4 }}>
                  {r.team} {r.is_home == null ? "" : r.is_home ? "vs" : "@"} {r.opponent ?? "—"} &middot; proj{" "}
                  {r.projected.toFixed(1)} &rarr; act {r.actual.toFixed(1)}
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{ fontSize: 32, fontWeight: 700, color: isOver ? "#3fdb9a" : "#f27587" }}>
                  {fmtDiff(r.diff)}
                </div>
                <div style={{ width: 120, height: 7, borderRadius: 4, background: "#1e2530", marginTop: 6, marginLeft: "auto", overflow: "hidden" }}>
                  <div
                    style={{
                      width: `${pct}%`,
                      height: "100%",
                      borderRadius: 4,
                      marginLeft: "auto",
                      background: isOver ? "#34c98e" : "#e8687c",
                    }}
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>
      <FooterBar />
    </Frame>
  );
}

function SpotlightSlide({ week, scoring, row }: { week: number; scoring: Scoring; row: ProjectionDiffRow }) {
  const isOver = row.diff >= 0;
  return (
    <Frame>
      <BrandBar week={week} scoring={scoring} />
      <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center" }}>
        <div style={{ fontFamily: "var(--font-mono), monospace", fontSize: 24, letterSpacing: "0.1em", color: "#e8a33d", marginBottom: 22 }}>
          NOBODY SAW THIS COMING
        </div>
        <div style={{ fontSize: 30, display: "flex", alignItems: "center", marginBottom: 8 }}>
          <PositionBadge position={row.position} />
          <span style={{ color: "#93a0b3" }}>
            {row.team} {row.is_home == null ? "" : row.is_home ? "vs" : "@"} {row.opponent ?? "—"}
          </span>
        </div>
        <div style={{ fontSize: 80, fontWeight: 700, lineHeight: 1.05, letterSpacing: "-0.01em" }}>{row.name}</div>

        <div style={{ display: "flex", gap: 24, marginTop: 56 }}>
          <div style={{ flex: 1, padding: "26px 28px", borderRadius: 20, background: "#141a22", border: "1px solid #262e39" }}>
            <div style={{ fontSize: 20, color: "#93a0b3" }}>Projected</div>
            <div style={{ fontFamily: "var(--font-mono), monospace", fontSize: 56, fontWeight: 700, marginTop: 6 }}>
              {row.projected.toFixed(1)}
            </div>
          </div>
          <div style={{ flex: 1, padding: "26px 28px", borderRadius: 20, background: "#141a22", border: "1px solid #262e39" }}>
            <div style={{ fontSize: 20, color: "#93a0b3" }}>Actual</div>
            <div style={{ fontFamily: "var(--font-mono), monospace", fontSize: 56, fontWeight: 700, marginTop: 6 }}>
              {row.actual.toFixed(1)}
            </div>
          </div>
        </div>
        <div
          style={{
            marginTop: 24,
            fontFamily: "var(--font-mono), monospace",
            fontSize: 44,
            fontWeight: 700,
            color: isOver ? "#3fdb9a" : "#f27587",
          }}
        >
          {fmtDiff(row.diff)} pts
        </div>
      </div>
      <FooterBar />
    </Frame>
  );
}

function CtaSlide({ week, scoring }: { week: number; scoring: Scoring }) {
  return (
    <Frame>
      <BrandBar week={week} scoring={scoring} />
      <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "flex-start" }}>
        <div style={{ fontSize: 68, fontWeight: 700, lineHeight: 1.12 }}>
          Full breakdown
          <br />
          at the link in bio
        </div>
        <div
          style={{
            marginTop: 40,
            fontFamily: "var(--font-mono), monospace",
            fontSize: 30,
            color: "#e8a33d",
            padding: "16px 26px",
            borderRadius: 999,
            border: "1px solid #3a2c14",
            background: "#1a150a",
          }}
        >
          roughdraftfootball.com
        </div>
      </div>
      <FooterBar />
    </Frame>
  );
}

function BoomBustContent() {
  const { week, season, scoring, slide, page, spotlightId } = useSlideParams();

  const seasonsQuery = useQuery({ queryKey: ["fantasy-seasons"], queryFn: fetchFantasySeasons });
  const resolvedSeason = season ?? seasonsQuery.data?.[0] ?? null;

  const diffQuery = useQuery({
    queryKey: ["projection-diff", resolvedSeason, week, scoring],
    queryFn: () => fetchProjectionDiff({ season: resolvedSeason as number, week: week as number, scoring }),
    enabled: resolvedSeason != null && week != null,
  });

  if (!week) {
    return <div style={{ padding: 40, color: "#e6e8eb" }}>Missing required ?week= param.</div>;
  }
  if (resolvedSeason == null || diffQuery.isLoading) {
    return <div style={{ padding: 40, color: "#e6e8eb" }}>Loading…</div>;
  }
  if (diffQuery.isError || !diffQuery.data) {
    return <div style={{ padding: 40, color: "#e6e8eb" }}>Couldn&apos;t load week {week}.</div>;
  }

  const rows = diffQuery.data.rows;
  const over = rows.filter((r) => r.diff >= 0);
  const under = [...rows].reverse().filter((r) => r.diff < 0);

  const start = (page - 1) * ROWS_PER_SLIDE;
  const overSlice = over.slice(start, start + ROWS_PER_SLIDE);
  const underSlice = under.slice(start, start + ROWS_PER_SLIDE);

  const spotlight = spotlightId ? rows.find((r) => r.gsis_id === spotlightId) : rows[0];

  switch (slide) {
    case "over":
      return <ListSlide week={week} scoring={scoring} kind="over" rows={overSlice} page={page} />;
    case "under":
      return <ListSlide week={week} scoring={scoring} kind="under" rows={underSlice} page={page} />;
    case "spotlight":
      return spotlight ? (
        <SpotlightSlide week={week} scoring={scoring} row={spotlight} />
      ) : (
        <div style={{ padding: 40, color: "#e6e8eb" }}>No spotlight player found.</div>
      );
    case "cta":
      return <CtaSlide week={week} scoring={scoring} />;
    case "cover":
    default:
      return <CoverSlide week={week} scoring={scoring} top={rows[0]} />;
  }
}

export default function BoomBustPage() {
  return (
    <React.Suspense fallback={<div style={{ padding: 40, color: "#e6e8eb" }}>Loading…</div>}>
      <BoomBustContent />
    </React.Suspense>
  );
}
