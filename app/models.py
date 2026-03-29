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
from sqlalchemy import DateTime, Enum as SAEnum, func, Boolean, Float, UniqueConstraint
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