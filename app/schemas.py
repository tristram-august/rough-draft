from __future__ import annotations

import re
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


# ── Blog ──────────────────────────────────────────────────────────────────────

PostStatusLiteral = Literal["draft", "published"]

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class PostIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    slug: str | None = Field(default=None, max_length=160)
    subtitle: str | None = Field(default=None, max_length=300)
    excerpt: str | None = Field(default=None, max_length=500)
    body_markdown: str = Field(default="", max_length=200_000)
    cover_image_url: str | None = Field(default=None, max_length=2000)
    status: PostStatusLiteral = "draft"
    tags: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("slug")
    @classmethod
    def slug_shape(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        v = v.strip().lower()
        if not _SLUG_RE.match(v):
            raise ValueError("Slug may only contain lowercase letters, numbers, and single hyphens")
        return v

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, v: list[str]) -> list[str]:
        out: list[str] = []
        for raw in v:
            tag = raw.strip().lower()
            if not tag:
                continue
            if len(tag) > 32:
                raise ValueError("Tags must be 32 characters or fewer")
            if tag not in out:
                out.append(tag)
        return out


class PostSummary(BaseModel):
    """Listing shape — no body, so the index stays light."""
    id: int
    slug: str
    title: str
    subtitle: str | None = None
    excerpt: str | None = None
    cover_image_url: str | None = None
    status: PostStatusLiteral
    author_username: str
    tags: list[str] = Field(default_factory=list)
    reading_minutes: int
    published_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class PostOut(PostSummary):
    body_markdown: str


class PostListOut(BaseModel):
    posts: list[PostSummary]
    total: int


class TagCountOut(BaseModel):
    tag: str
    count: int


# ── Fantasy ───────────────────────────────────────────────────────────────────

ScoringLiteral = Literal["ppr", "half", "std"]
FantasyPositionLiteral = Literal["ALL", "QB", "RB", "WR", "TE", "FLEX"]
FantasySortLiteral = Literal[
    "total",
    "ppg",
    "games",
    "name",
    "td",           # pass + rush + rec TDs combined
    "pass_yards",
    "pass_tds",
    "pass_ints",
    "rush_yards",
    "rush_tds",
    "receptions",
    "rec_yards",
    "rec_tds",
]
FantasyDirectionLiteral = Literal["asc", "desc"]


class FantasyStatLine(BaseModel):
    pass_yards: int = 0
    pass_tds: int = 0
    pass_ints: int = 0
    rush_yards: int = 0
    rush_tds: int = 0
    receptions: int = 0
    rec_yards: int = 0
    rec_tds: int = 0
    fumbles_lost: int = 0


class FantasyLeaderRow(BaseModel):
    rank: int
    gsis_id: str
    name: str
    position: str | None = None
    team: str | None = None
    headshot: str | None = None
    games: int
    fantasy_points: float
    points_per_game: float
    stats: FantasyStatLine


class FantasyLeaderboardOut(BaseModel):
    season: int
    week: int | None = None
    season_type: str
    scoring: ScoringLiteral
    position: FantasyPositionLiteral
    sort: FantasySortLiteral
    direction: FantasyDirectionLiteral = "desc"
    total: int
    rows: list[FantasyLeaderRow]


class FantasyGameRow(BaseModel):
    season: int
    week: int | None = None
    season_type: str | None = None
    team: str | None = None
    opponent: str | None = None
    fantasy_points: float
    stats: FantasyStatLine


class FantasyPlayerSeasonOut(BaseModel):
    season: int
    team: str | None = None
    games: int
    fantasy_points: float
    points_per_game: float
    stats: FantasyStatLine


class FantasyPlayerOut(BaseModel):
    gsis_id: str
    name: str
    position: str | None = None
    headshot: str | None = None
    scoring: ScoringLiteral
    seasons: list[FantasyPlayerSeasonOut]
    games: list[FantasyGameRow]


class FantasyScoringPresetOut(BaseModel):
    key: ScoringLiteral
    label: str
    points_per_reception: float


# ── Fantasy draft board (preseason ECR/ADP) ───────────────────────────────────

class FantasyBoardRow(BaseModel):
    overall_rank: int
    tier: int | None = None
    player_name: str
    team: str | None = None
    position: str
    position_rank: int | None = None
    bye_week: int | None = None
    sos: int | None = None
    ecr_vs_adp: int | None = None
    avg_diff: float | None = None
    gsis_id: str | None = None   # present when linked to production history


class FantasyBoardOut(BaseModel):
    season: int
    total: int
    positions: list[str]
    rows: list[FantasyBoardRow]


# ── Schedule ──────────────────────────────────────────────────────────────────

class GameOut(BaseModel):
    game_id: str
    season: int
    game_type: str | None = None
    week: int | None = None
    gameday: date | None = None
    weekday: str | None = None
    gametime: str | None = None          # US/Eastern, "20:20"
    kickoff_et: datetime | None = None   # gameday + gametime, naive Eastern

    away_team: str
    home_team: str
    away_name: str | None = None
    home_name: str | None = None
    away_score: int | None = None
    home_score: int | None = None
    final: bool = False

    spread_line: float | None = None
    total_line: float | None = None
    div_game: bool | None = None
    stadium: str | None = None


class UpcomingScheduleOut(BaseModel):
    season: int | None = None
    week: int | None = None
    game_type: str | None = None
    days_until_kickoff: int | None = None
    first_kickoff_et: datetime | None = None
    in_season: bool = False
    games: list[GameOut]


# ── Pick'em ───────────────────────────────────────────────────────────────────

class PickIn(BaseModel):
    picked_team: str = Field(min_length=2, max_length=8)


class PickSplitOut(BaseModel):
    """How the community split on a game."""
    away: int = 0
    home: int = 0
    total: int = 0


class SlateGameOut(GameOut):
    locked: bool = False           # kickoff has passed
    your_pick: str | None = None
    split: PickSplitOut
    winner: str | None = None      # set once final; None on a tie
    your_result: str | None = None  # "win" | "loss" | "push" once graded

    # Elo model's pre-game prediction (see app/elo.py), when one exists.
    model_home_win_prob: float | None = None
    model_favorite: str | None = None


class PredictionAccuracyOut(BaseModel):
    """Backtested Elo accuracy, straight-up, over an out-of-sample range —
    see scripts/build_elo_ratings.py for how the range and model constants
    were chosen (not fit to the numbers reported here)."""
    season_from: int
    season_to: int
    model_correct: int
    model_graded: int
    vegas_correct: int
    vegas_graded: int


class SlateOut(BaseModel):
    season: int | None = None
    week: int | None = None
    game_type: str | None = None
    games: list[SlateGameOut]


class PickLeaderRow(BaseModel):
    rank: int
    display_name: str
    voter_type: str
    is_you: bool = False
    wins: int
    losses: int
    pushes: int
    graded: int
    pct: float


class PickLeaderboardOut(BaseModel):
    season: int
    week: int | None = None
    scope: Literal["week", "season"]
    rows: list[PickLeaderRow]


# ── Power rankings ────────────────────────────────────────────────────────────

PowerSubjectLiteral = Literal["team", "player"]


class PowerSubjectOut(BaseModel):
    """Something rankable — a team or a player."""
    subject_id: str          # team abbrev, or gsis_id
    name: str
    subtitle: str | None = None   # team name for players, division for teams
    image: str | None = None


class PowerEntryOut(BaseModel):
    rank: int
    subject_id: str
    name: str
    subtitle: str | None = None
    image: str | None = None
    note: str | None = None

    previous_rank: int | None = None
    movement: int | None = None       # + is upward; None when there's no prior week
    consensus_rank: float | None = None
    consensus_ballots: int = 0
    your_rank: int | None = None


class PowerRankingOut(BaseModel):
    subject_type: PowerSubjectLiteral
    subject_group: str = ""
    season: int
    week: int | None = None
    has_official: bool = False
    author_username: str | None = None
    updated_at: datetime | None = None
    ballot_count: int = 0
    entries: list[PowerEntryOut]


class PowerBallotIn(BaseModel):
    """Ordered subject ids, best first. Rank is derived from position."""
    subject_ids: list[str] = Field(min_length=1, max_length=64)
    notes: dict[str, str] = Field(default_factory=dict)

    @field_validator("subject_ids")
    @classmethod
    def no_duplicates(cls, v: list[str]) -> list[str]:
        cleaned = [s.strip() for s in v if s and s.strip()]
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("A subject can only appear once in a ballot")
        return cleaned


class PowerScopeOut(BaseModel):
    """A season/week that has at least one ranking, for the picker."""
    season: int
    week: int | None = None
    has_official: bool = False
    ballot_count: int = 0


# ── Matchup stats ─────────────────────────────────────────────────────────────

class MatchupStatRowOut(BaseModel):
    stat_label: str
    team: str
    team_value: str
    team_rank: int | None = None
    opp_team: str
    opp_stat_label: str
    opp_value: str
    opp_rank: int | None = None
    # True when team_rank is the better (lower) of the two — None if either
    # side is unranked, so the client doesn't have to re-derive the tie rule.
    team_favored: bool | None = None


class MatchupStatCategoryOut(BaseModel):
    category: str
    rows: list[MatchupStatRowOut]


class MatchupStatsOut(BaseModel):
    game_id: str
    source_season: int | None = None
    categories: list[MatchupStatCategoryOut]


# ── News ──────────────────────────────────────────────────────────────────────

class NewsItemOut(BaseModel):
    headline: str
    description: str | None = None
    published: datetime | None = None
    url: str | None = None
    image: str | None = None
    source: str | None = None


class NewsFeedOut(BaseModel):
    items: list[NewsItemOut]
    fetched_at: datetime
    stale: bool = False   # served from cache after an upstream failure
    source: str = "ESPN, PFT"

