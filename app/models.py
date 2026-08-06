from __future__ import annotations

from datetime import date, datetime  # <-- add datetime here
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import DateTime, func, Boolean, Float, UniqueConstraint
import enum



class Base(DeclarativeBase):
    pass


class Team(Base):
    __tablename__ = "team"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    abbrev: Mapped[str] = mapped_column(String(8), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(64))
    city: Mapped[str] = mapped_column(String(64))
    conference: Mapped[str | None] = mapped_column(String(8), nullable=True)
    division: Mapped[str | None] = mapped_column(String(16), nullable=True)

    picks: Mapped[list["DraftPick"]] = relationship(back_populates="team", foreign_keys="DraftPick.team_id")


class Player(Base):
    __tablename__ = "player"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(128), index=True)
    position: Mapped[str] = mapped_column(String(8), index=True)
    college: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    birthdate: Mapped[date | None] = mapped_column(Date, nullable=True)
    gsis_id: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)

    stats: Mapped[list["PlayerSeasonStat"]] = relationship(back_populates="player")


class DraftPick(Base):
    __tablename__ = "draft_pick"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    year: Mapped[int] = mapped_column(Integer, index=True)
    round: Mapped[int] = mapped_column(Integer, index=True)
    pick_in_round: Mapped[int] = mapped_column(Integer)
    overall: Mapped[int] = mapped_column(Integer, index=True)

    team_id: Mapped[int] = mapped_column(ForeignKey("team.id"), index=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("player.id"), index=True)
    traded_from_team_id: Mapped[int | None] = mapped_column(ForeignKey("team.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    team: Mapped["Team"] = relationship(back_populates="picks", foreign_keys=[team_id])
    player: Mapped["Player"] = relationship(foreign_keys=[player_id])
    outcome: Mapped["PickOutcome | None"] = relationship(back_populates="pick", uselist=False)

    __table_args__ = (
        UniqueConstraint("year", "overall", name="uq_pick_year_overall"),
        CheckConstraint("round >= 1", name="ck_pick_round_ge_1"),
        CheckConstraint("overall >= 1", name="ck_pick_overall_ge_1"),
        Index("ix_pick_year_round_overall", "year", "round", "overall"),
        Index("ix_pick_team_year", "team_id", "year"),
    )


class PlayerSeasonStat(Base):
    __tablename__ = "player_season_stat"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("player.id"), index=True)
    season: Mapped[int] = mapped_column(Integer, index=True)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("team.id"), nullable=True)

    games: Mapped[int | None] = mapped_column(Integer, nullable=True)
    starts: Mapped[int | None] = mapped_column(Integer, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    player: Mapped["Player"] = relationship(back_populates="stats")

    __table_args__ = (
        UniqueConstraint("player_id", "season", name="uq_player_season"),
        Index("ix_stat_player_season", "player_id", "season"),
    )


class PickOutcome(Base):
    __tablename__ = "pick_outcome"

    pick_id: Mapped[int] = mapped_column(ForeignKey("draft_pick.id"), primary_key=True)
    outcome_score: Mapped[int] = mapped_column(Integer)  # 0..100
    label: Mapped[str] = mapped_column(String(16))       # Bust..Elite
    method_version: Mapped[str] = mapped_column(String(32), default="v1")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    pick: Mapped["DraftPick"] = relationship(back_populates="outcome")

    __table_args__ = (
        CheckConstraint("outcome_score >= 0 AND outcome_score <= 100", name="ck_outcome_score_0_100"),
        Index("ix_outcome_label", "label"),
    )
    
class VoteValue(str, enum.Enum):
    success = "success"
    bust = "bust"

class VoterType(str, enum.Enum):
    anon = "anon"
    user = "user"

class PickVote(Base):
    __tablename__ = "pick_vote"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pick_id: Mapped[int] = mapped_column(ForeignKey("draft_pick.id"), index=True)

    voter_type: Mapped[str] = mapped_column(String(8))  # "anon" | "user"
    voter_key: Mapped[str] = mapped_column(String(64))  # uuid or user id

    value: Mapped[str] = mapped_column(String(8))       # "success" | "bust"

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("pick_id", "voter_type", "voter_key", name="uq_vote_one_per_voter_per_pick"),
        Index("ix_vote_pick_value", "pick_id", "value"),
    )

class PlayerCareerSummary(Base):
    """
    Career-ish totals/awards snapshot from your yearly draft CSVs.

    Notes:
      - If your CSV values change over time (e.g., player still active), re-ingesting later years will update.
      - You can later replace/augment this with true season-by-season stats tables.
    """
    __tablename__ = "player_career_summary"

    player_id: Mapped[int] = mapped_column(ForeignKey("player.id"), primary_key=True)

    # Identifiers
    gsis_id: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    pfr_player_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    cfb_player_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    # Flags / accolades
    hof: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    allpro: Mapped[int | None] = mapped_column(Integer, nullable=True)
    probowls: Mapped[int | None] = mapped_column(Integer, nullable=True)
    seasons_started: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # AV-like
    w_av: Mapped[float | None] = mapped_column(Float, nullable=True)
    car_av: Mapped[float | None] = mapped_column(Float, nullable=True)
    dr_av: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Totals
    games: Mapped[int | None] = mapped_column(Integer, nullable=True)

    pass_completions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pass_attempts: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pass_yards: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pass_tds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pass_ints: Mapped[int | None] = mapped_column(Integer, nullable=True)

    rush_atts: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rush_yards: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rush_tds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    receptions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rec_yards: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rec_tds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def_solo_tackles: Mapped[int | None] = mapped_column(Integer, nullable=True)
    def_ints: Mapped[int | None] = mapped_column(Integer, nullable=True)
    def_sacks: Mapped[float | None] = mapped_column(Float, nullable=True)

    player: Mapped["Player"] = relationship()

class PlayerDim(Base):
    """
    Canonical player identity / bio / IDs, keyed by gsis_id.
    Source: players_NFL.csv
    """
    __tablename__ = "player_dim"

    gsis_id: Mapped[str] = mapped_column(String(16), primary_key=True)

    # External IDs (nullable)
    pfr_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    espn_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    pff_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    nfl_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)

    # Names
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    first_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    short_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    football_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    suffix: Mapped[str | None] = mapped_column(String(16), nullable=True)

    # Bio
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight: Mapped[int | None] = mapped_column(Integer, nullable=True)
    headshot: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Football
    position: Mapped[str | None] = mapped_column(String(8), nullable=True, index=True)
    position_group: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    ngs_position: Mapped[str | None] = mapped_column(String(16), nullable=True)
    ngs_position_group: Mapped[str | None] = mapped_column(String(16), nullable=True)

    # Status / current
    latest_team: Mapped[str | None] = mapped_column(String(8), nullable=True, index=True)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ngs_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ngs_status_short_description: Mapped[str | None] = mapped_column(String(64), nullable=True)
    years_of_experience: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rookie_season: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_season: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Draft metadata
    draft_year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    draft_round: Mapped[int | None] = mapped_column(Integer, nullable=True)
    draft_pick: Mapped[int | None] = mapped_column(Integer, nullable=True)
    draft_team: Mapped[str | None] = mapped_column(String(8), nullable=True, index=True)

    # School
    college_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    college_conference: Mapped[str | None] = mapped_column(String(64), nullable=True)

    jersey_number: Mapped[int | None] = mapped_column(Integer, nullable=True)


class PlayerGameStat(Base):
    """
    Game-by-game stats subset for drawer.
    Source: player_stats_YYYY.csv (2000+)
    """
    __tablename__ = "player_game_stat"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Join keys
    player_gsis_id: Mapped[str] = mapped_column(ForeignKey("player_dim.gsis_id"), index=True)
    season: Mapped[int] = mapped_column(Integer, index=True)
    week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    season_type: Mapped[str | None] = mapped_column(String(8), nullable=True)  # REG / POST etc

    game_id: Mapped[str] = mapped_column(String(32), index=True)
    team: Mapped[str] = mapped_column(String(8), index=True)
    opponent_team: Mapped[str | None] = mapped_column(String(8), nullable=True)

    position_group: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)

    # Core passing
    pass_completions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pass_attempts: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pass_yards: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pass_tds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pass_ints: Mapped[int | None] = mapped_column(Integer, nullable=True)
    passing_epa: Mapped[float | None] = mapped_column(Float, nullable=True)
    passing_cpoe: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Core rushing
    rush_attempts: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rush_yards: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rush_tds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rushing_epa: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Core receiving (volume-first + optional value)
    targets: Mapped[int | None] = mapped_column(Integer, nullable=True)
    receptions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rec_yards: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rec_tds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    receiving_epa: Mapped[float | None] = mapped_column(Float, nullable=True)

    target_share: Mapped[float | None] = mapped_column(Float, nullable=True)
    air_yards: Mapped[int | None] = mapped_column(Integer, nullable=True)
    air_yards_share: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Ball security
    fumbles_lost: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Defense (splash + basics)
    def_tackles: Mapped[int | None] = mapped_column(Integer, nullable=True)
    def_sacks: Mapped[float | None] = mapped_column(Float, nullable=True)
    def_ints: Mapped[int | None] = mapped_column(Integer, nullable=True)
    def_forced_fumbles: Mapped[int | None] = mapped_column(Integer, nullable=True)
    def_fumble_recoveries: Mapped[int | None] = mapped_column(Integer, nullable=True)
    def_tds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint("player_gsis_id", "game_id", "team", name="uq_player_game_team"),
        Index("ix_pgs_player_season", "player_gsis_id", "season"),
        Index("ix_pgs_player_team_season", "player_gsis_id", "team", "season"),
    )


class OLSeasonStat(Base):
    """Season-level OL blocking stats from PFF."""
    __tablename__ = "ol_season_stat"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("player.id"), index=True)
    pff_player_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    season: Mapped[int] = mapped_column(Integer, index=True)
    position: Mapped[str | None] = mapped_column(String(4), nullable=True)
    team_abbrev: Mapped[str | None] = mapped_column(String(8), nullable=True)

    games: Mapped[int | None] = mapped_column(Integer, nullable=True)
    snap_counts_offense: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pressures_allowed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hurries_allowed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hits_allowed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sacks_allowed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pbe: Mapped[float | None] = mapped_column(Float, nullable=True)
    pass_block_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    penalties: Mapped[int | None] = mapped_column(Integer, nullable=True)

    player: Mapped["Player"] = relationship()

    __table_args__ = (
        UniqueConstraint("player_id", "season", name="uq_ol_player_season"),
    )


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(128), nullable=False)
    is_mod: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    verify_token: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    reset_token: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    reset_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    comments: Mapped[list["Comment"]] = relationship(back_populates="author")


class PowerRanking(Base):
    """
    One ordered ballot. Deliberately generic: `subject_type` + `subject_group`
    mean team rankings and positional (QB, RB, ...) rankings share this table and
    every endpoint below, instead of positional rankings needing a second schema.

    is_official marks the site's editorial list; everything else is a user ballot,
    and the consensus is averaged across those.
    """
    __tablename__ = "power_ranking"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    subject_type: Mapped[str] = mapped_column(String(16), index=True)          # "team" | "player"
    subject_group: Mapped[str] = mapped_column(String(16), server_default="")  # "" for teams, "QB" etc

    season: Mapped[int] = mapped_column(Integer, index=True)
    week: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    author_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    is_official: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    author: Mapped["User"] = relationship()
    entries: Mapped[list["PowerRankingEntry"]] = relationship(
        back_populates="ranking", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        UniqueConstraint(
            "subject_type", "subject_group", "season", "week", "author_id",
            name="uq_power_ranking_ballot",
        ),
        Index("ix_power_scope", "subject_type", "subject_group", "season", "week"),
    )


class PowerRankingEntry(Base):
    __tablename__ = "power_ranking_entry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ranking_id: Mapped[int] = mapped_column(
        ForeignKey("power_ranking.id", ondelete="CASCADE"), index=True
    )

    rank: Mapped[int] = mapped_column(Integer)
    # Team abbrev or gsis_id, depending on the parent's subject_type.
    subject_id: Mapped[str] = mapped_column(String(32), index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    ranking: Mapped["PowerRanking"] = relationship(back_populates="entries")

    __table_args__ = (
        UniqueConstraint("ranking_id", "rank", name="uq_power_entry_rank"),
        UniqueConstraint("ranking_id", "subject_id", name="uq_power_entry_subject"),
    )


class GamePick(Base):
    """
    A straight-up winner pick for one game. Mirrors PickVote's anon/user shape so
    the same X-Client-Id flow works here.
    """
    __tablename__ = "game_pick"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[str] = mapped_column(ForeignKey("game.game_id"), index=True)

    voter_type: Mapped[str] = mapped_column(String(8))   # "anon" | "user"
    voter_key: Mapped[str] = mapped_column(String(64))   # client uuid, or user id as text

    picked_team: Mapped[str] = mapped_column(String(8))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("game_id", "voter_type", "voter_key", name="uq_pick_one_per_voter_per_game"),
        Index("ix_game_pick_voter", "voter_type", "voter_key"),
    )


class FantasyRank(Base):
    """
    Preseason fantasy draft board for a season — ECR/ADP cheat sheet data.
    Distinct from PlayerGameStat-derived rankings, which are what actually
    happened; this is what the market expects before a ball is snapped.
    """
    __tablename__ = "fantasy_rank"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    season: Mapped[int] = mapped_column(Integer, index=True)

    overall_rank: Mapped[int] = mapped_column(Integer)
    tier: Mapped[int | None] = mapped_column(Integer, nullable=True)

    player_name: Mapped[str] = mapped_column(String(128), index=True)
    team: Mapped[str | None] = mapped_column(String(8), nullable=True)  # "FA" for free agents
    position: Mapped[str] = mapped_column(String(8), index=True)        # QB/RB/WR/TE/K/DST
    position_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)

    bye_week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sos: Mapped[int | None] = mapped_column(Integer, nullable=True)        # 0-5
    ecr_vs_adp: Mapped[int | None] = mapped_column(Integer, nullable=True)  # +/- slots
    avg_diff: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Best-effort link to player_dim so a board row can reach production history.
    gsis_id: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)

    __table_args__ = (
        UniqueConstraint("season", "overall_rank", name="uq_fantasy_rank_season_rank"),
        Index("ix_fantasy_rank_season_pos", "season", "position"),
    )


class Game(Base):
    """
    Schedule + result for a single game, from the nflverse games.csv feed.
    game_id matches PlayerGameStat.game_id (e.g. "2026_01_NE_SEA").
    """
    __tablename__ = "game"

    game_id: Mapped[str] = mapped_column(String(32), primary_key=True)

    season: Mapped[int] = mapped_column(Integer, index=True)
    game_type: Mapped[str | None] = mapped_column(String(8), nullable=True)  # REG/WC/DIV/CON/SB
    week: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    gameday: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    weekday: Mapped[str | None] = mapped_column(String(12), nullable=True)
    gametime: Mapped[str | None] = mapped_column(String(8), nullable=True)  # "20:20", US/Eastern

    away_team: Mapped[str] = mapped_column(String(8), index=True)
    home_team: Mapped[str] = mapped_column(String(8), index=True)
    away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result: Mapped[float | None] = mapped_column(Float, nullable=True)  # home margin
    overtime: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    spread_line: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_line: Mapped[float | None] = mapped_column(Float, nullable=True)

    div_game: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    roof: Mapped[str | None] = mapped_column(String(16), nullable=True)
    surface: Mapped[str | None] = mapped_column(String(24), nullable=True)
    stadium: Mapped[str | None] = mapped_column(String(64), nullable=True)
    location: Mapped[str | None] = mapped_column(String(16), nullable=True)

    away_qb_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    home_qb_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    away_coach: Mapped[str | None] = mapped_column(String(64), nullable=True)
    home_coach: Mapped[str | None] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        Index("ix_game_season_week", "season", "week"),
        Index("ix_game_gameday", "gameday"),
    )


class MatchupStat(Base):
    """
    One row of a team-comparison stat sheet for a game, scraped from a
    third-party site (see scripts/ingest_matchup_stats.py). `team` is whichever
    side "owns" the primary stat_label — `opp_team`'s number is that same stat
    family for the other side (often their allowed/defensive version, e.g.
    "Opp Points/Game"), not a duplicate. Each category+team pairing produces
    one row per stat, so a full 6-category matchup is ~2 rows per stat (one
    per team's CSV) x ~5-8 stats x 6 categories.

    team_rank/opp_rank are what "who has the edge" is judged on — lower rank
    always means better-in-the-league for that specific stat regardless of
    whether it's an offensive or defensive metric, since the source data
    already normalizes direction into the rank. Raw values stay as scraped
    strings (%, +/-, decimals all vary) since they're display-only.
    """
    __tablename__ = "matchup_stat"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[str] = mapped_column(ForeignKey("game.game_id"), index=True)

    category: Mapped[str] = mapped_column(String(16), index=True)  # Overall/Passing/Rushing/Kicking/Penalties/Turnovers
    stat_label: Mapped[str] = mapped_column(String(64))

    team: Mapped[str] = mapped_column(String(8))
    team_value: Mapped[str] = mapped_column(String(24))
    team_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)

    opp_team: Mapped[str] = mapped_column(String(8))
    opp_stat_label: Mapped[str] = mapped_column(String(64))
    opp_value: Mapped[str] = mapped_column(String(24))
    opp_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)

    source_season: Mapped[int] = mapped_column(Integer)  # season the stat DATA is from, e.g. 2025

    __table_args__ = (
        UniqueConstraint("game_id", "category", "stat_label", "team", name="uq_matchup_stat_row"),
        Index("ix_matchup_stat_game", "game_id"),
    )


class NewsCache(Base):
    """
    Last-good payload from the unofficial ESPN news feed (see app/api_news.py).
    Single row (id=1), overwritten on every successful upstream fetch, so a
    fresh container that boots straight into an ESPN block still has
    yesterday's headlines to serve instead of an empty widget.
    """
    __tablename__ = "news_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    items_json: Mapped[str] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EloRating(Base):
    """
    A team's current Elo rating (see app/elo.py), as of its most recent game
    processed by scripts/build_elo_ratings.py. One row per team; rebuilt from
    scratch each time that script runs, not appended to.
    """
    __tablename__ = "elo_rating"

    team: Mapped[str] = mapped_column(String(8), primary_key=True)
    rating: Mapped[float] = mapped_column(Float)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class GamePrediction(Base):
    """
    The Elo model's pre-game prediction for one game, plus (once the game is
    final) how it and the Vegas closing line each did. Covers both historical
    games — the backtest, exposed via /api/predictions/accuracy — and
    upcoming games, where actual_winner/correct/vegas_correct stay null until
    build_elo_ratings.py is rerun after the game finishes.
    """
    __tablename__ = "game_prediction"

    game_id: Mapped[str] = mapped_column(ForeignKey("game.game_id"), primary_key=True)

    home_elo_pre: Mapped[float] = mapped_column(Float)
    away_elo_pre: Mapped[float] = mapped_column(Float)
    home_win_prob: Mapped[float] = mapped_column(Float)
    predicted_winner: Mapped[str] = mapped_column(String(8))

    actual_winner: Mapped[str | None] = mapped_column(String(8), nullable=True)
    correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Vegas closing spread_line's implied favorite, for the same game — the
    # baseline the model is honestly measured against, not just itself.
    vegas_favorite: Mapped[str | None] = mapped_column(String(8), nullable=True)
    vegas_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)


class Post(Base):
    """A blog post, authored in markdown by a mod."""
    __tablename__ = "post"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True, nullable=False)

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    subtitle: Mapped[str | None] = mapped_column(String(300), nullable=True)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_markdown: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    cover_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="draft")  # draft | published

    author_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True, nullable=False)

    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    author: Mapped["User"] = relationship()
    tags: Mapped[list["PostTag"]] = relationship(
        back_populates="post", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        CheckConstraint("status IN ('draft', 'published')", name="ck_post_status"),
        Index("ix_post_status_published", "status", "published_at"),
    )


class PostTag(Base):
    __tablename__ = "post_tag"

    post_id: Mapped[int] = mapped_column(ForeignKey("post.id", ondelete="CASCADE"), primary_key=True)
    tag: Mapped[str] = mapped_column(String(32), primary_key=True)

    post: Mapped["Post"] = relationship(back_populates="tags")

    __table_args__ = (
        Index("ix_post_tag_tag", "tag"),
    )


class Comment(Base):
    __tablename__ = "comment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pick_id: Mapped[int] = mapped_column(ForeignKey("draft_pick.id"), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    author: Mapped["User"] = relationship(back_populates="comments")
    pick: Mapped["DraftPick"] = relationship()

    __table_args__ = (
        CheckConstraint("char_length(body) >= 1", name="ck_comment_body_not_empty"),
        Index("ix_comment_pick_created", "pick_id", "created_at"),
    )


class PostComment(Base):
    __tablename__ = "post_comment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("post.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    author: Mapped["User"] = relationship()
    post: Mapped["Post"] = relationship()

    __table_args__ = (
        CheckConstraint("char_length(body) >= 1", name="ck_post_comment_body_not_empty"),
        Index("ix_post_comment_post_created", "post_id", "created_at"),
    )


class PostLike(Base):
    """
    A single like on a blog post. Anonymous-friendly, same identity shape as
    PickVote (liker_type "anon"|"user", liker_key = client uuid or user id as
    text) but boolean rather than valued — no updated_at, since a like has no
    in-place-editable value, only insert (like) or delete (unlike).
    """
    __tablename__ = "post_like"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("post.id", ondelete="CASCADE"), index=True, nullable=False)
    liker_type: Mapped[str] = mapped_column(String(8))   # "anon" | "user"
    liker_key: Mapped[str] = mapped_column(String(64))   # uuid or user id
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("post_id", "liker_type", "liker_key", name="uq_like_one_per_liker_per_post"),
    )