from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DraftPick, Player, PlayerCareerSummary, Team

TEAM_ABBREV_NORMALIZE: dict[str, str] = {
    # common historical / provider abbreviations -> modern canonical
    "NWE": "NE",
    "GNB": "GB",
    "KAN": "KC",
    "NOR": "NO",
    "SFO": "SF",
    "TAM": "TB",
    "SDG": "LAC",
    "STL": "LAR",
    "OAK": "LV",
    "RAI": "LV",
    "LVR": "LV",  # observed in your 2025 file
    "JAC": "JAX",
    "WSH": "WAS",
}

TEAM_META: dict[str, dict[str, str | None]] = {
    "ARI": {"city": "Arizona", "name": "Cardinals", "conference": "NFC", "division": "West"},
    "ATL": {"city": "Atlanta", "name": "Falcons", "conference": "NFC", "division": "South"},
    "BAL": {"city": "Baltimore", "name": "Ravens", "conference": "AFC", "division": "North"},
    "BUF": {"city": "Buffalo", "name": "Bills", "conference": "AFC", "division": "East"},
    "CAR": {"city": "Carolina", "name": "Panthers", "conference": "NFC", "division": "South"},
    "CHI": {"city": "Chicago", "name": "Bears", "conference": "NFC", "division": "North"},
    "CIN": {"city": "Cincinnati", "name": "Bengals", "conference": "AFC", "division": "North"},
    "CLE": {"city": "Cleveland", "name": "Browns", "conference": "AFC", "division": "North"},
    "DAL": {"city": "Dallas", "name": "Cowboys", "conference": "NFC", "division": "East"},
    "DEN": {"city": "Denver", "name": "Broncos", "conference": "AFC", "division": "West"},
    "DET": {"city": "Detroit", "name": "Lions", "conference": "NFC", "division": "North"},
    "GB": {"city": "Green Bay", "name": "Packers", "conference": "NFC", "division": "North"},
    "HOU": {"city": "Houston", "name": "Texans", "conference": "AFC", "division": "South"},
    "IND": {"city": "Indianapolis", "name": "Colts", "conference": "AFC", "division": "South"},
    "JAX": {"city": "Jacksonville", "name": "Jaguars", "conference": "AFC", "division": "South"},
    "KC": {"city": "Kansas City", "name": "Chiefs", "conference": "AFC", "division": "West"},
    "LAC": {"city": "Los Angeles", "name": "Chargers", "conference": "AFC", "division": "West"},
    "LAR": {"city": "Los Angeles", "name": "Rams", "conference": "NFC", "division": "West"},
    "LV": {"city": "Las Vegas", "name": "Raiders", "conference": "AFC", "division": "West"},
    "MIA": {"city": "Miami", "name": "Dolphins", "conference": "AFC", "division": "East"},
    "MIN": {"city": "Minnesota", "name": "Vikings", "conference": "NFC", "division": "North"},
    "NE": {"city": "New England", "name": "Patriots", "conference": "AFC", "division": "East"},
    "NO": {"city": "New Orleans", "name": "Saints", "conference": "NFC", "division": "South"},
    "NYG": {"city": "New York", "name": "Giants", "conference": "NFC", "division": "East"},
    "NYJ": {"city": "New York", "name": "Jets", "conference": "AFC", "division": "East"},
    "PHI": {"city": "Philadelphia", "name": "Eagles", "conference": "NFC", "division": "East"},
    "PIT": {"city": "Pittsburgh", "name": "Steelers", "conference": "AFC", "division": "North"},
    "SEA": {"city": "Seattle", "name": "Seahawks", "conference": "NFC", "division": "West"},
    "SF": {"city": "San Francisco", "name": "49ers", "conference": "NFC", "division": "West"},
    "TB": {"city": "Tampa Bay", "name": "Buccaneers", "conference": "NFC", "division": "South"},
    "TEN": {"city": "Tennessee", "name": "Titans", "conference": "AFC", "division": "South"},
    "WAS": {"city": "Washington", "name": "Commanders", "conference": "NFC", "division": "East"},
}

REQUIRED_COLS = {
    "season",
    "round",
    "pick",  # overall pick number in your files
    "team",
    "pfr_player_name",
    "position",
}

CAREER_COLS = [
    "gsis_id",
    "pfr_player_id",
    "cfb_player_id",
    "hof",
    "allpro",
    "probowls",
    "seasons_started",
    "w_av",
    "car_av",
    "dr_av",
    "games",
    "pass_completions",
    "pass_attempts",
    "pass_yards",
    "pass_tds",
    "pass_ints",
    "rush_atts",
    "rush_yards",
    "rush_tds",
    "receptions",
    "rec_yards",
    "rec_tds",
    "def_solo_tackles",
    "def_ints",
    "def_sacks",
]


def normalize_team_abbrev(raw: str) -> str:
    raw = (raw or "").strip().upper()
    return TEAM_ABBREV_NORMALIZE.get(raw, raw)


def _as_int(v: Any) -> int | None:
    if pd.isna(v):
        return None
    try:
        return int(float(v))
    except Exception:
        return None


def _as_float(v: Any) -> float | None:
    if pd.isna(v):
        return None
    try:
        return float(v)
    except Exception:
        return None


def _as_bool01(v: Any) -> bool | None:
    if pd.isna(v):
        return None
    s = str(v).strip()
    if s in {"0", "0.0"}:
        return False
    if s in {"1", "1.0"}:
        return True
    return None


async def upsert_team(session: AsyncSession, *, abbrev: str) -> Team:
    res = await session.execute(select(Team).where(Team.abbrev == abbrev))
    team = res.scalars().first()
    meta = TEAM_META.get(abbrev)

    if team:
        if meta:
            team.city = meta["city"] or team.city
            team.name = meta["name"] or team.name
            team.conference = meta["conference"]
            team.division = meta["division"]
        return team

    if not meta:
        meta = {"city": abbrev, "name": abbrev, "conference": None, "division": None}

    team = Team(
        abbrev=abbrev,
        city=str(meta["city"] or abbrev),
        name=str(meta["name"] or abbrev),
        conference=meta["conference"],
        division=meta["division"],
    )
    session.add(team)
    await session.flush()
    return team


async def upsert_player_from_row(session: AsyncSession, row: dict[str, Any]) -> Player:
    full_name = str(row.get("pfr_player_name") or "").strip()
    position = str(row.get("position") or "").strip().upper()
    college = row.get("college")
    college = None if pd.isna(college) else str(college)

    # best-effort identity: pfr_player_id if present, else (name, position)
    pfr_id_raw = row.get("pfr_player_id")
    pfr_id = None if pd.isna(pfr_id_raw) else str(pfr_id_raw).strip()

    if pfr_id:
        # your Player model doesn't have pfr_id; keep matching stable-ish for now.
        stmt = select(Player).where(Player.full_name == full_name, Player.position == position)
    else:
        stmt = select(Player).where(Player.full_name == full_name, Player.position == position)

    res = await session.execute(stmt)
    player = res.scalars().first()

    if player:
        player.college = college or player.college
        return player

    player = Player(full_name=full_name, position=position, college=college)
    session.add(player)
    await session.flush()
    return player


async def upsert_pick(
    session: AsyncSession,
    *,
    year: int,
    overall: int,
    round_num: int,
    pick_in_round: int,
    team_id: int,
    player_id: int,
    team_raw: str,
) -> DraftPick:
    res = await session.execute(select(DraftPick).where(DraftPick.year == year, DraftPick.overall == overall))
    pick = res.scalars().first()

    notes = None
    raw_up = (team_raw or "").strip().upper()
    if raw_up and normalize_team_abbrev(raw_up) != raw_up:
        notes = f"team_raw={raw_up}"

    if pick:
        pick.round = round_num
        pick.pick_in_round = pick_in_round
        pick.team_id = team_id
        pick.player_id = player_id
        if notes:
            pick.notes = (pick.notes + " | " + notes) if pick.notes else notes
        return pick

    pick = DraftPick(
        year=year,
        round=round_num,
        pick_in_round=pick_in_round,
        overall=overall,
        team_id=team_id,
        player_id=player_id,
        notes=notes,
    )
    session.add(pick)
    await session.flush()
    return pick


async def upsert_career_summary(session: AsyncSession, *, player_id: int, row: dict[str, Any]) -> None:
    res = await session.execute(select(PlayerCareerSummary).where(PlayerCareerSummary.player_id == player_id))
    cs = res.scalars().first()
    if not cs:
        cs = PlayerCareerSummary(player_id=player_id)
        session.add(cs)

    cs.gsis_id = None if pd.isna(row.get("gsis_id")) else str(row.get("gsis_id")).strip()
    cs.pfr_player_id = None if pd.isna(row.get("pfr_player_id")) else str(row.get("pfr_player_id")).strip()
    cs.cfb_player_id = _as_int(row.get("cfb_player_id"))

    cs.hof = _as_bool01(row.get("hof"))
    cs.allpro = _as_int(row.get("allpro"))
    cs.probowls = _as_int(row.get("probowls"))
    cs.seasons_started = _as_int(row.get("seasons_started"))

    cs.w_av = _as_float(row.get("w_av"))
    cs.car_av = _as_float(row.get("car_av"))
    cs.dr_av = _as_float(row.get("dr_av"))
    cs.games = _as_int(row.get("games"))

    cs.pass_completions = _as_int(row.get("pass_completions"))
    cs.pass_attempts = _as_int(row.get("pass_attempts"))
    cs.pass_yards = _as_int(row.get("pass_yards"))
    cs.pass_tds = _as_int(row.get("pass_tds"))
    cs.pass_ints = _as_int(row.get("pass_ints"))

    cs.rush_atts = _as_int(row.get("rush_atts"))
    cs.rush_yards = _as_int(row.get("rush_yards"))
    cs.rush_tds = _as_int(row.get("rush_tds"))

    cs.receptions = _as_int(row.get("receptions"))
    cs.rec_yards = _as_int(row.get("rec_yards"))
    cs.rec_tds = _as_int(row.get("rec_tds"))

    cs.def_solo_tackles = _as_int(row.get("def_solo_tackles"))
    cs.def_ints = _as_int(row.get("def_ints"))
    cs.def_sacks = _as_float(row.get("def_sacks"))


def _compute_pick_in_round(df: pd.DataFrame) -> pd.Series:
    """
    Your CSV 'pick' is overall pick number.
    Compute pick_in_round as 1..N within each (season, round) ordered by overall pick.
    """
    return (
        df.sort_values(["season", "round", "pick"])
        .groupby(["season", "round"])
        .cumcount()
        .add(1)
        .reindex(df.sort_values(["season", "round", "pick"]).index)
    )


async def ingest_csv_file(session: AsyncSession, *, csv_path: Path) -> int:
    df = pd.read_csv(csv_path)

    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"{csv_path.name}: missing required columns: {sorted(missing)}")

    # enforce types-ish
    df["season"] = df["season"].astype(int)
    df["round"] = df["round"].astype(int)
    df["pick"] = df["pick"].astype(int)

    # compute pick_in_round
    df = df.sort_values(["season", "round", "pick"]).reset_index(drop=True)
    df["pick_in_round"] = df.groupby(["season", "round"]).cumcount() + 1

    count = 0
    for row in df.to_dict(orient="records"):
        year = int(row["season"])
        round_num = int(row["round"])
        overall = int(row["pick"])

        team_raw = str(row["team"])
        team_abbrev = normalize_team_abbrev(team_raw)

        player = await upsert_player_from_row(session, row)
        team = await upsert_team(session, abbrev=team_abbrev)

        await upsert_pick(
            session,
            year=year,
            overall=overall,
            round_num=round_num,
            pick_in_round=int(row["pick_in_round"]),
            team_id=team.id,
            player_id=player.id,
            team_raw=team_raw,
        )

        await upsert_career_summary(session, player_id=player.id, row=row)
        count += 1

    return count


async def ingest_csv_dir(session: AsyncSession, *, csv_dir: Path) -> dict[str, int]:
    results: dict[str, int] = {}
    for csv_path in sorted(csv_dir.glob("*.csv")):
        n = await ingest_csv_file(session, csv_path=csv_path)
        results[csv_path.name] = n
    return results