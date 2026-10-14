"use client";

import * as React from "react";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google";
import { fetchFantasySeasons, fetchProjectionDiff, type ProjectionDiffRow, type Scoring } from "../../lib/fantasy";

const plexSans = IBM_Plex_Sans({ subsets: ["latin"], weight: ["400", "500", "600", "700"], variable: "--font-sans" });
const plexMono = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400", "500", "600", "700"], variable: "--font-mono" });

const PANEL_WIDTH = 520;
const DEFAULT_MIN_PROJECTED = 30;
const DEFAULT_LIMIT = 6;

const POSITION_COLORS: Record<string, { bg: string; fg: string }> = {
  QB: { bg: "#3a2440", fg: "#d89ff0" },
  RB: { bg: "#123326", fg: "#4fe0a0" },
  WR: { bg: "#122f3a", fg: "#5cc3ef" },
  TE: { bg: "#3a2c14", fg: "#f0b95c" },
  K: { bg: "#1e232b", fg: "#9aa5b4" },
  DST: { bg: "#2c1f3a", fg: "#c79ff5" },
};

type Kind = "over" | "under" | "met";

const KIND_STYLE: Record<Kind, { label: string; dot: string; text: string; bar: string }> = {
  over: { label: "Outperformed", dot: "#0f9d63", text: "#0f9d63", bar: "#34c98e" },
  under: { label: "Underperformed", dot: "#d6455a", text: "#d6455a", bar: "#e8687c" },
  met: { label: "Closest to Projection", dot: "#b3791a", text: "#b3791a", bar: "#caa358" },
};

function fmtDiff(n: number) {
  const s = n.toFixed(1);
  return n > 0 ? `+${s}` : s;
}

function useParams() {
  const params = useSearchParams();
  const seasonParam = params.get("season");
  const scoring = (params.get("scoring") as Scoring | null) ?? "ppr";
  const kind = (params.get("kind") as Kind | null) ?? "over";
  const minProjected = Number(params.get("minProjected") ?? String(DEFAULT_MIN_PROJECTED)) || DEFAULT_MIN_PROJECTED;
  const limit = Number(params.get("limit") ?? String(DEFAULT_LIMIT)) || DEFAULT_LIMIT;
  return { season: seasonParam ? Number(seasonParam) : null, scoring, kind, minProjected, limit };
}

function PositionBadge({ position }: { position: string }) {
  const c = POSITION_COLORS[position] ?? { bg: "#1e232b", fg: "#9aa5b4" };
  return (
    <span
      style={{
        display: "inline-block",
        fontSize: 10,
        fontWeight: 700,
        letterSpacing: "0.03em",
        padding: "1.5px 6px",
        borderRadius: 4,
        background: c.bg,
        color: c.fg,
        marginRight: 6,
        verticalAlign: 1,
      }}
    >
      {position}
    </span>
  );
}

function Row({ rank, row, kind, maxAbs, showGames }: { rank: number; row: ProjectionDiffRow; kind: Kind; maxAbs: number; showGames: boolean }) {
  const style = KIND_STYLE[kind];
  const pct = Math.min(100, Math.round((Math.abs(row.diff) / maxAbs) * 100));
  return (
    <li
      style={{
        display: "grid",
        gridTemplateColumns: "22px 1fr auto",
        alignItems: "center",
        gap: 10,
        padding: "9px 10px",
        borderRadius: 9,
      }}
    >
      <span style={{ fontSize: 11, color: "#8b94a3", fontFamily: "var(--font-mono), monospace", textAlign: "right" }}>{rank}</span>
      <div style={{ minWidth: 0 }}>
        <div style={{ fontSize: 13.5, fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
          <PositionBadge position={row.position} />
          {row.name}
        </div>
        <div style={{ fontSize: 11, color: "#8b94a3", marginTop: 1 }}>
          {row.team}
          {row.opponent ? ` ${row.is_home ? "vs" : "@"} ${row.opponent}` : ""} &middot; proj{" "}
          {row.projected.toFixed(1)} &rarr; act {row.actual.toFixed(1)}
          {showGames && ` · ${row.games} gm${row.games === 1 ? "" : "s"}`}
        </div>
      </div>
      <div style={{ textAlign: "right" }}>
        <div style={{ fontSize: 14, fontWeight: 700, color: style.text }}>{fmtDiff(row.diff)}</div>
        <div style={{ width: 64, height: 4, borderRadius: 2, background: "#f7f8fa10", marginTop: 4, marginLeft: "auto", overflow: "hidden" }}>
          <div style={{ width: `${pct}%`, height: "100%", borderRadius: 2, marginLeft: "auto", background: style.bar }} />
        </div>
      </div>
    </li>
  );
}

function Panel({ kind, rows, periodLabel, showGames }: { kind: Kind; rows: ProjectionDiffRow[]; periodLabel: string; showGames: boolean }) {
  const style = KIND_STYLE[kind];
  const maxAbs = Math.max(1, ...rows.map((r) => Math.abs(r.diff)));
  return (
    <div
      className={`${plexSans.variable} ${plexMono.variable}`}
      data-slide-ready="true"
      style={{
        width: PANEL_WIDTH,
        background: "#141a22",
        border: "1px solid #262e39",
        borderRadius: 14,
        overflow: "hidden",
        fontFamily: "var(--font-sans), sans-serif",
        color: "#e6e8eb",
        boxSizing: "border-box",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "13px 16px",
          borderBottom: "1px solid #262e39",
          background: "#1a212b",
        }}
      >
        <span style={{ width: 8, height: 8, borderRadius: "50%", background: style.dot }} />
        <h3 style={{ fontSize: 13, margin: 0, fontWeight: 650 }}>{style.label}</h3>
        <span style={{ marginLeft: "auto", fontSize: 11, color: "#5f6b7d", fontFamily: "var(--font-mono), monospace" }}>
          {periodLabel} &middot; top {rows.length}
        </span>
      </div>
      <ul style={{ listStyle: "none", margin: 0, padding: 6 }}>
        {rows.map((r, i) => (
          <Row key={r.gsis_id} rank={i + 1} row={r} kind={kind} maxAbs={maxAbs} showGames={showGames} />
        ))}
      </ul>
    </div>
  );
}

function SeasonPanelContent() {
  const { season, scoring, kind, minProjected, limit } = useParams();
  const seasonsQuery = useQuery({ queryKey: ["fantasy-seasons"], queryFn: fetchFantasySeasons });
  const resolvedSeason = season ?? seasonsQuery.data?.[0] ?? null;

  const diffQuery = useQuery({
    queryKey: ["projection-diff", resolvedSeason, scoring],
    queryFn: () => fetchProjectionDiff({ season: resolvedSeason as number, week: null, scoring }),
    enabled: resolvedSeason != null,
  });

  if (resolvedSeason == null || diffQuery.isLoading) {
    return <div style={{ padding: 20, color: "#e6e8eb" }}>Loading…</div>;
  }
  if (diffQuery.isError || !diffQuery.data) {
    return <div style={{ padding: 20, color: "#e6e8eb" }}>Couldn&apos;t load projection data.</div>;
  }

  // Kickers have no field-goal/extra-point columns in the scoring engine, so
  // their actual points always compute to 0 -- that's a scoring gap, not a
  // real miss, and it dominates season-long bust lists if left in.
  const rows = diffQuery.data.rows.filter((r) => r.position !== "K" && r.position !== "DST");
  const weeks = diffQuery.data.weeks;
  const periodLabel = weeks.length > 1 ? `Weeks ${weeks[0]}–${weeks[weeks.length - 1]}` : `Week ${weeks[0] ?? ""}`;

  let selected: ProjectionDiffRow[];
  if (kind === "over") {
    selected = rows.filter((r) => r.diff >= 0).slice(0, limit);
  } else if (kind === "under") {
    selected = [...rows].reverse().filter((r) => r.diff < 0).slice(0, limit);
  } else {
    selected = rows
      .filter((r) => r.projected >= minProjected)
      .sort((a, b) => Math.abs(a.diff) - Math.abs(b.diff))
      .slice(0, limit);
  }

  return (
    <div style={{ background: "#0d1117", display: "inline-block", padding: 1 }}>
      <Panel kind={kind} rows={selected} periodLabel={periodLabel} showGames />
    </div>
  );
}

export default function SeasonPanelPage() {
  return (
    <React.Suspense fallback={<div style={{ padding: 20, color: "#e6e8eb" }}>Loading…</div>}>
      <SeasonPanelContent />
    </React.Suspense>
  );
}
