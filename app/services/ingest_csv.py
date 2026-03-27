from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DraftPick, Player, Team

# If you already added PlayerCareerSummary, keep this import.
# If you do NOT have it yet, comment out the next line and the related code block.
from app.models import PlayerCareerSummary  # type: ignore


TEAM_ABBREV_NORMALIZE: dict[str, str] = {
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
    "LVR": "LV",
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

REQUIRED_COLS = {"season", "round", "pick", "team", "pfr_player_name", "position"}


def normalize_team_abbrev(raw: str) -> str:
    raw = (raw or "").strip().upper()
    return TEAM_ABBREV_NORMALIZE.get(raw, raw)


def _s(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


def _i(v: Any) -> int | None:
    s = _s(v)
    if s is None:
        return None
    try:
        return int(float(s))
    except Exception:
        return None


def _f(v: Any) -> float | None:
    s = _s(v)
    if s is None:
        return None
    try:
        return float(s)
    except Exception:
        return None


def _b01(v: Any) -> bool | None:
    s = _s(v)
    if s is None:
        return None
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


async def upsert_player(session: AsyncSession, *, full_name: str, position: str, college: str | None) -> Player:
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


async def upsert_career_summary_if_available(session: AsyncSession, *, player_id: int, row: dict[str, Any]) -> None:
    """
    Optional: only works if you created PlayerCareerSummary model/table.
    If you haven't added that model yet, comment out its import and calls.
    """
    res = await session.execute(select(PlayerCareerSummary).where(PlayerCareerSummary.player_id == player_id))
    cs = res.scalars().first()
    if not cs:
        cs = PlayerCareerSummary(player_id=player_id)
        session.add(cs)

    # ids
    cs.gsis_id = _s(row.get("gsis_id"))
    cs.pfr_player_id = _s(row.get("pfr_player_id"))
    cs.cfb_player_id = _i(row.get("cfb_player_id"))

    # flags / accolades
    cs.hof = _b01(row.get("hof"))
    cs.allpro = _i(row.get("allpro"))
    cs.probowls = _i(row.get("probowls"))
    cs.seasons_started = _i(row.get("seasons_started"))

    # AV
    cs.w_av = _f(row.get("w_av"))
    cs.car_av = _f(row.get("car_av"))
    cs.dr_av = _f(row.get("dr_av"))

    # totals
    cs.games = _i(row.get("games"))

    cs.pass_completions = _i(row.get("pass_completions"))
    cs.pass_attempts = _i(row.get("pass_attempts"))
    cs.pass_yards = _i(row.get("pass_yards"))
    cs.pass_tds = _i(row.get("pass_tds"))
    cs.pass_ints = _i(row.get("pass_ints"))

    cs.rush_atts = _i(row.get("rush_atts"))
    cs.rush_yards = _i(row.get("rush_yards"))
    cs.rush_tds = _i(row.get("rush_tds"))

    cs.receptions = _i(row.get("receptions"))
    cs.rec_yards = _i(row.get("rec_yards"))
    cs.rec_tds = _i(row.get("rec_tds"))

    cs.def_solo_tackles = _i(row.get("def_solo_tackles"))
    cs.def_ints = _i(row.get("def_ints"))
    cs.def_sacks = _f(row.get("def_sacks"))


def read_csv_rows(csv_path: Path) -> list[dict[str, Any]]:
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"{csv_path.name}: missing header row")

        missing = REQUIRED_COLS - set(reader.fieldnames)
        if missing:
            raise ValueError(f"{csv_path.name}: missing required columns: {sorted(missing)}")

        return [row for row in reader]


def compute_pick_in_round(rows: list[dict[str, Any]]) -> None:
    """
    Your CSV contains overall 'pick' but not 'pick_in_round'.
    We compute it by sorting by (season, round, pick) then counting within (season, round).
    """
    rows.sort(key=lambda r: (int(float(r["season"])), int(float(r["round"])), int(float(r["pick"]))))

    counters: dict[tuple[int, int], int] = {}
    for r in rows:
        season = int(float(r["season"]))
        rnd = int(float(r["round"]))
        key = (season, rnd)
        counters[key] = counters.get(key, 0) + 1
        r["pick_in_round"] = str(counters[key])


async def ingest_csv_file(session: AsyncSession, *, csv_path: Path) -> int:
    rows = read_csv_rows(csv_path)
    compute_pick_in_round(rows)

    count = 0
    for row in rows:
        year = int(float(row["season"]))
        round_num = int(float(row["round"]))
        overall = int(float(row["pick"]))

        team_raw = str(row["team"])
        team_abbrev = normalize_team_abbrev(team_raw)

        full_name = (row.get("pfr_player_name") or "").strip()
        position = (row.get("position") or "").strip().upper()
        college = _s(row.get("college"))

        team = await upsert_team(session, abbrev=team_abbrev)
        player = await upsert_player(session, full_name=full_name, position=position, college=college)

        await upsert_pick(
            session,
            year=year,
            overall=overall,
            round_num=round_num,
            pick_in_round=int(float(row["pick_in_round"])),
            team_id=team.id,
            player_id=player.id,
            team_raw=team_raw,
        )

        # Optional career summary
        await upsert_career_summary_if_available(session, player_id=player.id, row=row)

        count += 1

    return count


async def ingest_csv_dir(session: AsyncSession, *, csv_dir: Path) -> dict[str, int]:
    results: dict[str, int] = {}
    for csv_path in sorted(csv_dir.glob("*.csv")):
        n = await ingest_csv_file(session, csv_path=csv_path)
        results[csv_path.name] = n
    return results