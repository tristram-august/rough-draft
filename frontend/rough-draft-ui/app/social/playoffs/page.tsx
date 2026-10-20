"use client";

import * as React from "react";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google";
import { fetchPlayoffOdds, fmtProb, fmtRecord, type PlayoffOdds, type PlayoffTeamOdds } from "../../lib/playoffs";
import { teamColor } from "../../lib/team-colors";

const plexSans = IBM_Plex_Sans({ subsets: ["latin"], weight: ["400", "500", "600", "700"], variable: "--font-sans" });
const plexMono = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400", "500", "600", "700"], variable: "--font-mono" });

// Same validated categorical slots and alphabetical team order as the Playoffs tab, so colors match the site.
const SERIES = ["#3987e5", "#d95926", "#199e70", "#c98500"];
const POS = "57, 135, 229";

type Conference = "AFC" | "NFC";
type Slide = "cover" | "table" | "division" | "cta" | "panel-table" | "panel-division";

const weekLabel = (w: number) => (w === 0 ? "Preseason" : `After Week ${w}`);
const heat = (p: number, max = 0.5) => ({ background: `rgba(${POS}, ${(p * max).toFixed(3)})` });

function Frame({ children }: { children: React.ReactNode }) {
  return (
    <div
      className={`${plexSans.variable} ${plexMono.variable}`}
      data-slide-ready="true"
      style={{
        width: 1080, height: 1350, background: "#0d1117", color: "#e6e8eb",
        fontFamily: "var(--font-sans), sans-serif", display: "flex", flexDirection: "column",
        padding: "72px 76px", boxSizing: "border-box", position: "relative", overflow: "hidden",
      }}
    >
      {children}
    </div>
  );
}

function BrandBar({ right }: { right: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
      <div style={{ fontFamily: "var(--font-mono), monospace", fontSize: 22, letterSpacing: "0.14em", color: "#e8a33d", fontWeight: 600 }}>
        ROUGH DRAFT FOOTBALL
      </div>
      <div style={{ fontFamily: "var(--font-mono), monospace", fontSize: 20, color: "#5f6b7d", textTransform: "uppercase" }}>{right}</div>
    </div>
  );
}

function FooterBar() {
  return (
    <div
      style={{
        position: "absolute", left: 76, right: 76, bottom: 56, display: "flex", justifyContent: "space-between",
        fontFamily: "var(--font-mono), monospace", fontSize: 18, color: "#5f6b7d",
      }}
    >
      <span>roughdraftfootball.com</span>
      <span>10,000 simulated seasons · Elo</span>
    </div>
  );
}

function OddsLines({
  teams,
  weeks,
  width,
  height,
  font,
}: {
  teams: PlayoffTeamOdds[];
  weeks: number[];
  width: number;
  height: number;
  font: number;
}) {
  const padL = font * 3.2;
  const padR = font * 5;
  const padT = font;
  const padB = font * 2.2;
  const n = weeks.length;
  const x = (i: number) => padL + (n > 1 ? (i / (n - 1)) * (width - padL - padR) : (width - padL - padR) / 2);
  const y = (p: number) => padT + (1 - p) * (height - padT - padB);
  const ordered = [...teams].sort((a, b) => a.team.localeCompare(b.team));
  const valueAt = (t: PlayoffTeamOdds, i: number) => t.history.find((h) => h.week === weeks[i])?.make_playoffs ?? null;
  const ends = ordered.map((t, k) => ({ t, k, y: y(valueAt(t, n - 1) ?? 0) })).sort((a, b) => a.y - b.y);
  for (let i = 1; i < ends.length; i++) ends[i].y = Math.max(ends[i].y, ends[i - 1].y + font * 1.15);
  const overflow = ends.length ? ends[ends.length - 1].y - (height - padB) : 0;
  if (overflow > 0) ends.forEach((e) => (e.y -= overflow));
  const stroke = Math.max(2, font / 6);

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{ display: "block" }}>
      {[0, 0.5, 1].map((p) => (
        <g key={p}>
          <line x1={padL} x2={width - padR} y1={y(p)} y2={y(p)} stroke={p === 0.5 ? "#2a3442" : "#1e2530"} strokeWidth={1} />
          <text x={padL - font * 0.5} y={y(p) + font * 0.35} textAnchor="end" fontSize={font * 0.85} fill="#5f6b7d" fontFamily="var(--font-mono), monospace">
            {p * 100}%
          </text>
        </g>
      ))}
      {weeks.map((w, i) => (
        <text key={w} x={x(i)} y={height - font * 0.5} textAnchor="middle" fontSize={font * 0.85} fill="#5f6b7d" fontFamily="var(--font-mono), monospace">
          {w === 0 ? "Pre" : w}
        </text>
      ))}
      {ordered.map((t, k) => {
        const pts = weeks.map((_, i) => valueAt(t, i)).map((v, i) => (v == null ? null : ([x(i), y(v)] as const)));
        const d = pts.filter(Boolean).map((p, i) => `${i ? "L" : "M"}${p![0].toFixed(1)},${p![1].toFixed(1)}`).join(" ");
        const last = pts[pts.length - 1];
        return (
          <g key={t.team}>
            <path d={d} fill="none" stroke={SERIES[k]} strokeWidth={stroke} strokeLinejoin="round" strokeLinecap="round" />
            {last && <circle cx={last[0]} cy={last[1]} r={stroke * 2} fill={SERIES[k]} stroke="#0d1117" strokeWidth={stroke} />}
          </g>
        );
      })}
      {ends.map(({ t, k, y: ly }) => (
        <g key={t.team}>
          <rect x={width - padR + font * 0.6} y={ly - font * 0.38} width={font * 0.76} height={font * 0.76} rx={font * 0.18} fill={SERIES[k]} />
          <text x={width - padR + font * 1.7} y={ly + font * 0.36} fontSize={font} fill="#cbd5e1" fontWeight={600}>
            {t.team}
          </text>
        </g>
      ))}
    </svg>
  );
}

function movers(teams: PlayoffTeamOdds[], week: number) {
  const delta = (t: PlayoffTeamOdds) => {
    const now = t.history.find((h) => h.week === week)?.make_playoffs;
    const prev = t.history.find((h) => h.week === week - 1)?.make_playoffs;
    return now != null && prev != null ? now - prev : 0;
  };
  const sorted = [...teams].sort((a, b) => delta(b) - delta(a));
  return { riser: sorted[0], riserDelta: delta(sorted[0]), faller: sorted[sorted.length - 1], fallerDelta: delta(sorted[sorted.length - 1]) };
}

function Card({ label, team, value, sub, tone }: { label: string; team: PlayoffTeamOdds; value: string; sub: string; tone: string }) {
  return (
    <div style={{ flex: 1, padding: "26px 28px", borderRadius: 20, background: "#141a22", border: "1px solid #262e39" }}>
      <div style={{ fontSize: 20, color: "#93a0b3" }}>{label}</div>
      <div style={{ display: "flex", alignItems: "center", gap: 14, marginTop: 12 }}>
        <span style={{ width: 8, height: 40, borderRadius: 4, background: teamColor(team.team) }} />
        <span style={{ fontSize: 34, fontWeight: 650 }}>{team.team_name ?? team.team}</span>
      </div>
      <div style={{ marginTop: 14, fontFamily: "var(--font-mono), monospace", fontSize: 40, fontWeight: 700, color: tone }}>{value}</div>
      <div style={{ marginTop: 4, fontSize: 19, color: "#5f6b7d" }}>{sub}</div>
    </div>
  );
}

function CoverSlide({ conf, data, teams }: { conf: Conference; data: PlayoffOdds; teams: PlayoffTeamOdds[] }) {
  const top = teams[0];
  const m = movers(teams, data.week);
  const pts = (d: number) => `${d >= 0 ? "+" : "−"}${Math.abs(Math.round(d * 100))} pts`;
  return (
    <Frame>
      <BrandBar right={`${data.season} · ${weekLabel(data.week)}`} />
      <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center" }}>
        <div style={{ fontFamily: "var(--font-mono), monospace", fontSize: 24, letterSpacing: "0.1em", color: "#e8a33d", marginBottom: 18 }}>
          PLAYOFF ODDS
        </div>
        <div style={{ fontSize: 96, fontWeight: 700, lineHeight: 1.02, letterSpacing: "-0.01em" }}>
          {conf} Playoff
          <br />
          Picture
        </div>
        <div style={{ marginTop: 22, fontSize: 26, color: "#93a0b3" }}>{weekLabel(data.week)} · {data.sims.toLocaleString()} simulated seasons</div>
        <div style={{ marginTop: 52, padding: "26px 28px", borderRadius: 20, background: "#141a22", border: "1px solid #262e39" }}>
          <div style={{ fontSize: 20, color: "#93a0b3" }}>Most likely to make it</div>
          <div style={{ display: "flex", alignItems: "center", gap: 14, marginTop: 12 }}>
            <span style={{ width: 8, height: 40, borderRadius: 4, background: teamColor(top.team) }} />
            <span style={{ fontSize: 38, fontWeight: 650 }}>{top.team_name ?? top.team}</span>
            <span style={{ marginLeft: "auto", fontFamily: "var(--font-mono), monospace", fontSize: 44, fontWeight: 700 }}>{fmtProb(top.make_playoffs)}</span>
          </div>
        </div>
        {data.week > 0 && (
          <div style={{ display: "flex", gap: 22, marginTop: 22 }}>
            <Card label="Biggest riser this week" team={m.riser} value={pts(m.riserDelta)} sub={`now ${fmtProb(m.riser.make_playoffs)} to make it`} tone="#6da7ec" />
            <Card label="Biggest drop this week" team={m.faller} value={pts(m.fallerDelta)} sub={`now ${fmtProb(m.faller.make_playoffs)} to make it`} tone="#f27587" />
          </div>
        )}
      </div>
      <FooterBar />
    </Frame>
  );
}

const COLS = [
  { key: "make_playoffs", label: "Playoffs" },
  { key: "win_division", label: "Win Div" },
  { key: "first_seed", label: "Bye" },
  { key: "win_super_bowl", label: "Win SB" },
] as const;

function OddsTable({ teams, scale }: { teams: PlayoffTeamOdds[]; scale: number }) {
  const s = (n: number) => n * scale;
  const grid = `${s(250)}px ${s(76)}px repeat(4, 1fr)`;
  return (
    <div>
      <div
        style={{
          display: "grid", gridTemplateColumns: grid, gap: s(6), padding: `0 ${s(10)}px ${s(8)}px`,
          fontFamily: "var(--font-mono), monospace", fontSize: s(13), letterSpacing: "0.04em", color: "#5f6b7d", textTransform: "uppercase",
          whiteSpace: "nowrap",
        }}
      >
        <span>Team</span>
        <span style={{ textAlign: "right" }}>Record</span>
        {COLS.map((c) => <span key={c.key} style={{ textAlign: "center" }}>{c.label}</span>)}
      </div>
      {teams.map((t, i) => (
        <div
          key={t.team}
          style={{
            display: "grid", gridTemplateColumns: grid, gap: s(6), alignItems: "center", padding: `${s(4)}px ${s(10)}px`,
            borderTop: i === 7 ? `${s(2)}px dashed #3a4656` : `1px solid #1a212b`,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: s(10), minWidth: 0 }}>
            <span style={{ width: s(5), height: s(24), borderRadius: s(3), background: teamColor(t.team), flex: "none" }} />
            <span style={{ fontSize: s(17), fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{t.team_name ?? t.team}</span>
          </div>
          <span style={{ textAlign: "right", fontFamily: "var(--font-mono), monospace", fontSize: s(15), color: "#cbd5e1" }}>{fmtRecord(t.wins, t.losses)}</span>
          {COLS.map((c, j) => (
            <span
              key={c.key}
              style={{
                textAlign: "center", fontFamily: "var(--font-mono), monospace", fontSize: s(15), padding: `${s(5)}px 0`,
                borderRadius: s(6), fontWeight: j === 0 ? 700 : 500, color: "#f1f5f9", ...heat(t[c.key]),
              }}
            >
              {fmtProb(t[c.key])}
            </span>
          ))}
        </div>
      ))}
    </div>
  );
}

function TableSlide({ conf, data, teams }: { conf: Conference; data: PlayoffOdds; teams: PlayoffTeamOdds[] }) {
  return (
    <Frame>
      <BrandBar right={`${conf} · ${weekLabel(data.week)}`} />
      <div style={{ marginTop: 34, fontSize: 52, fontWeight: 700 }}>{conf} Playoff Odds</div>
      <div style={{ marginTop: 6, fontSize: 21, color: "#93a0b3" }}>Seven teams make it. The dashed line falls after the top seven.</div>
      <div style={{ marginTop: 26 }}>
        <OddsTable teams={teams} scale={1.4} />
      </div>
      <FooterBar />
    </Frame>
  );
}

function DivisionSlide({ conf, division, data, teams }: { conf: Conference; division: string; data: PlayoffOdds; teams: PlayoffTeamOdds[] }) {
  const weeks = data.weeks.filter((w) => w <= data.week);
  const ordered = [...teams].sort((a, b) => b.make_playoffs - a.make_playoffs);
  const colorOf = (t: PlayoffTeamOdds) => SERIES[[...teams].sort((a, b) => a.team.localeCompare(b.team)).indexOf(t)];
  return (
    <Frame>
      <BrandBar right={`${conf} · ${weekLabel(data.week)}`} />
      <div style={{ marginTop: 34, fontSize: 52, fontWeight: 700 }}>{conf} {division}</div>
      <div style={{ marginTop: 6, fontSize: 21, color: "#93a0b3" }}>Chance to make the playoffs, week by week</div>
      <div style={{ marginTop: 30 }}>
        <OddsLines teams={teams} weeks={weeks} width={928} height={560} font={26} />
      </div>
      <div style={{ marginTop: 28, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        {ordered.map((t) => (
          <div key={t.team} style={{ display: "flex", alignItems: "center", gap: 14, padding: "16px 20px", borderRadius: 14, background: "#141a22", border: "1px solid #1e2530" }}>
            <span style={{ width: 14, height: 14, borderRadius: 3, background: colorOf(t), flex: "none" }} />
            <div style={{ minWidth: 0 }}>
              <div style={{ fontSize: 24, fontWeight: 600 }}>{t.team_name ?? t.team}</div>
              <div style={{ fontFamily: "var(--font-mono), monospace", fontSize: 18, color: "#5f6b7d", marginTop: 2 }}>
                {fmtRecord(t.wins, t.losses)} · div {fmtProb(t.win_division)}
              </div>
            </div>
            <div style={{ marginLeft: "auto", fontFamily: "var(--font-mono), monospace", fontSize: 32, fontWeight: 700 }}>{fmtProb(t.make_playoffs)}</div>
          </div>
        ))}
      </div>
      <FooterBar />
    </Frame>
  );
}

function CtaSlide({ conf, data }: { conf: Conference; data: PlayoffOdds }) {
  return (
    <Frame>
      <BrandBar right={`${conf} · ${weekLabel(data.week)}`} />
      <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "flex-start" }}>
        <div style={{ fontSize: 68, fontWeight: 700, lineHeight: 1.12 }}>
          Every team&apos;s odds,
          <br />
          updated weekly
        </div>
        <div style={{ marginTop: 22, fontSize: 26, color: "#93a0b3" }}>Division races, bye chances and Super Bowl odds — link in bio</div>
        <div
          style={{
            marginTop: 40, fontFamily: "var(--font-mono), monospace", fontSize: 30, color: "#e8a33d",
            padding: "16px 26px", borderRadius: 999, border: "1px solid #3a2c14", background: "#1a150a",
          }}
        >
          roughdraftfootball.com/playoffs
        </div>
      </div>
      <FooterBar />
    </Frame>
  );
}

function Panel({ title, sub, width, children }: { title: string; sub: string; width: number; children: React.ReactNode }) {
  return (
    <div
      className={`${plexSans.variable} ${plexMono.variable}`}
      data-slide-ready="true"
      style={{
        width, background: "#141a22", border: "1px solid #262e39", borderRadius: 14, overflow: "hidden",
        fontFamily: "var(--font-sans), sans-serif", color: "#e6e8eb",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "13px 16px", borderBottom: "1px solid #262e39", background: "#1a212b" }}>
        <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#e8a33d" }} />
        <span style={{ fontSize: 13, fontWeight: 650 }}>{title}</span>
        <span style={{ marginLeft: "auto", fontSize: 10.5, color: "#5f6b7d", fontFamily: "var(--font-mono), monospace" }}>{sub}</span>
      </div>
      <div style={{ padding: "14px 16px 12px" }}>{children}</div>
      <div style={{ padding: "9px 16px 12px", borderTop: "1px solid #262e39", fontSize: 9.5, color: "#5f6b7d", lineHeight: 1.5 }}>
        From 10,000 simulations of the rest of the season using the site&apos;s Elo ratings. roughdraftfootball.com/playoffs
      </div>
    </div>
  );
}

function PlayoffSocialContent() {
  const params = useSearchParams();
  const conf = (params.get("conf") === "NFC" ? "NFC" : "AFC") as Conference;
  const slide = (params.get("slide") as Slide | null) ?? "cover";
  const division = params.get("division") ?? "East";
  const weekParam = params.get("week");
  const week = weekParam != null && weekParam !== "" ? Number(weekParam) : null;

  const q = useQuery({ queryKey: ["playoff-odds", week], queryFn: () => fetchPlayoffOdds(week) });
  if (q.isLoading) return <div style={{ padding: 40, color: "#e6e8eb" }}>Loading…</div>;
  if (q.isError || !q.data) return <div style={{ padding: 40, color: "#e6e8eb" }}>Couldn&apos;t load playoff odds.</div>;

  const data = q.data;
  const teams = data.teams.filter((t) => t.conference === conf);
  const divTeams = teams.filter((t) => t.division === division);
  const weeks = data.weeks.filter((w) => w <= data.week);

  switch (slide) {
    case "table":
      return <TableSlide conf={conf} data={data} teams={teams} />;
    case "division":
      return <DivisionSlide conf={conf} division={division} data={data} teams={divTeams} />;
    case "cta":
      return <CtaSlide conf={conf} data={data} />;
    case "panel-table":
      return (
        <Panel title={`${conf} Playoff Odds`} sub={`${data.season} · ${weekLabel(data.week)}`} width={640}>
          <OddsTable teams={teams} scale={0.95} />
        </Panel>
      );
    case "panel-division":
      return (
        <Panel title={`${conf} ${division}: Playoff Odds by Week`} sub={`${data.season} · ${weekLabel(data.week)}`} width={540}>
          <OddsLines teams={divTeams} weeks={weeks} width={506} height={250} font={12} />
        </Panel>
      );
    case "cover":
    default:
      return <CoverSlide conf={conf} data={data} teams={teams} />;
  }
}

export default function PlayoffSocialPage() {
  return (
    <React.Suspense fallback={<div style={{ padding: 40, color: "#e6e8eb" }}>Loading…</div>}>
      <PlayoffSocialContent />
    </React.Suspense>
  );
}
