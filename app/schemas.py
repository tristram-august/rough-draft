from __future__ import annotations

from datetime import date
from pydantic import BaseModel, Field
from typing import Literal


class TeamOut(BaseModel):
    id: int
    abbrev: str
    name: str
    city: str
    conference: str | None = None
    division: str | None = None


class PlayerOut(BaseModel):
    id: int
    full_name: str
    position: str
    college: str | None = None
    birthdate: date | None = None
    gsis_id: str | None = None


class OutcomeOut(BaseModel):
    outcome_score: int = Field(ge=0, le=100)
    label: str
    method_version: str
    notes: str | None = None


class DraftBoardRow(BaseModel):
    year: int
    round: int
    overall: int
    pick_in_round: int

    team: TeamOut
    player: PlayerOut
    traded_from_team: TeamOut | None = None
    outcome: OutcomeOut | None = None
    community_votes: CommunityVotesOut | None = None
    your_vote: VoteOut | None = None


class PickDetail(BaseModel):
    year: int
    round: int
    overall: int
    pick_in_round: int
    team: TeamOut
    player: PlayerOut
    traded_from_team: TeamOut | None = None
    notes: str | None = None
    outcome: OutcomeOut | None = None
    community_votes: CommunityVotesOut | None = None
    your_vote: VoteOut | None = None


class PlayerSeasonStatOut(BaseModel):
    season: int
    team_id: int | None = None
    games: int | None = None
    starts: int | None = None
    note: str | None = None


class PlayerDetail(BaseModel):
    player: PlayerOut
    draft_picks: list[DraftBoardRow]
    season_stats: list[PlayerSeasonStatOut]


class TeamDraftClass(BaseModel):
    team: TeamOut
    year: int
    picks: list[DraftBoardRow]
    
VoteValueLiteral = Literal["success", "bust"]

class VoteIn(BaseModel):
    value: VoteValueLiteral

class CommunityVotesOut(BaseModel):
    success: int = Field(ge=0)
    bust: int = Field(ge=0)
    total: int = Field(ge=0)
    community_score: int = Field(ge=0, le=100)  # % success
    community_label: str

class VoteOut(BaseModel):
    value: VoteValueLiteral




