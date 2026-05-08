from __future__ import annotations

from datetime import date, datetime
from pydantic import BaseModel, Field, field_validator
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
    voting_locked: bool = False

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
    voting_locked: bool = False
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


# ── OL Stats ──────────────────────────────────────────────────────────────────

class OLSeasonStatOut(BaseModel):
    season: int
    position: str | None = None
    team_abbrev: str | None = None
    games: int | None = None
    snap_counts_offense: int | None = None
    pressures_allowed: int | None = None
    hurries_allowed: int | None = None
    hits_allowed: int | None = None
    sacks_allowed: int | None = None
    pbe: float | None = None
    pass_block_percent: float | None = None
    penalties: int | None = None


# ── Auth ──────────────────────────────────────────────────────────────────────

class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    email: str = Field(min_length=5, max_length=128)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username may only contain letters, numbers, hyphens, and underscores")
        return v


class LoginIn(BaseModel):
    username: str
    password: str


class ForgotPasswordIn(BaseModel):
    email: str = Field(min_length=5, max_length=128)


class ResetPasswordIn(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    is_mod: bool = False
    email_verified: bool = False


# ── Comments ──────────────────────────────────────────────────────────────────

class CommentIn(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class CommentOut(BaseModel):
    id: int
    pick_id: int
    user_id: int
    username: str
    body: str
    created_at: datetime
    updated_at: datetime


# ── Profile ───────────────────────────────────────────────────────────────────

class ProfileVoteOut(BaseModel):
    year: int
    overall: int
    pick_in_round: int
    round: int
    player_name: str
    team_abbrev: str
    value: str          # "success" | "bust"
    voted_at: datetime

class ProfileCommentOut(BaseModel):
    id: int
    year: int
    overall: int
    pick_in_round: int
    round: int
    player_name: str
    team_abbrev: str
    body: str
    created_at: datetime

class ProfileOut(BaseModel):
    username: str
    joined_at: datetime
    total_votes: int
    total_success: int
    total_bust: int
    total_comments: int
    votes: list[ProfileVoteOut]
    comments: list[ProfileCommentOut]

