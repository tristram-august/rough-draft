from __future__ import annotations

from app.models import DraftPick, Team
from app.schemas import DraftBoardRow, OutcomeOut, PickDetail, PlayerOut, TeamOut
from app.settings import settings


def _voting_locked(year: int) -> bool:
    return year >= settings.voting_lock_from_year


def team_out(team: Team) -> TeamOut:
    return TeamOut(
        id=team.id,
        abbrev=team.abbrev,
        name=team.name,
        city=team.city,
        conference=team.conference,
        division=team.division,
    )


def pick_to_board_row(pick: DraftPick, traded_from_team: Team | None = None) -> DraftBoardRow:
    return DraftBoardRow(
        year=pick.year,
        round=pick.round,
        overall=pick.overall,
        pick_in_round=pick.pick_in_round,
        voting_locked=_voting_locked(pick.year),
        team=team_out(pick.team),
        player=PlayerOut(
            id=pick.player.id,
            full_name=pick.player.full_name,
            position=pick.player.position,
            college=pick.player.college,
            birthdate=pick.player.birthdate,
            gsis_id=pick.player.gsis_id,
        ),
        traded_from_team=team_out(traded_from_team) if traded_from_team else None,
        outcome=OutcomeOut(
            outcome_score=pick.outcome.outcome_score,
            label=pick.outcome.label,
            method_version=pick.outcome.method_version,
            notes=pick.outcome.notes,
        )
        if pick.outcome
        else None,
    )


def pick_to_detail(pick: DraftPick, traded_from_team: Team | None = None) -> PickDetail:
    row = pick_to_board_row(pick, traded_from_team=traded_from_team)
    return PickDetail(
        year=row.year,
        round=row.round,
        overall=row.overall,
        pick_in_round=row.pick_in_round,
        voting_locked=row.voting_locked,
        team=row.team,
        player=row.player,
        traded_from_team=row.traded_from_team,
        notes=pick.notes,
        outcome=row.outcome,
    )
