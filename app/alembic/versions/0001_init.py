from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "team",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("abbrev", sa.String(length=8), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("city", sa.String(length=64), nullable=False),
        sa.Column("conference", sa.String(length=8), nullable=True),
        sa.Column("division", sa.String(length=16), nullable=True),
    )
    op.create_index("ix_team_abbrev", "team", ["abbrev"], unique=True)

    op.create_table(
        "player",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("full_name", sa.String(length=128), nullable=False),
        sa.Column("position", sa.String(length=8), nullable=False),
        sa.Column("college", sa.String(length=128), nullable=True),
        sa.Column("birthdate", sa.Date(), nullable=True),
    )
    op.create_index("ix_player_full_name", "player", ["full_name"], unique=False)
    op.create_index("ix_player_position", "player", ["position"], unique=False)
    op.create_index("ix_player_college", "player", ["college"], unique=False)

    op.create_table(
        "draft_pick",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("round", sa.Integer(), nullable=False),
        sa.Column("pick_in_round", sa.Integer(), nullable=False),
        sa.Column("overall", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("team.id"), nullable=False),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("player.id"), nullable=False),
        sa.Column("traded_from_team_id", sa.Integer(), sa.ForeignKey("team.id"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint("round >= 1", name="ck_pick_round_ge_1"),
        sa.CheckConstraint("overall >= 1", name="ck_pick_overall_ge_1"),
        sa.UniqueConstraint("year", "overall", name="uq_pick_year_overall"),
    )
    op.create_index("ix_draft_pick_year", "draft_pick", ["year"], unique=False)
    op.create_index("ix_draft_pick_round", "draft_pick", ["round"], unique=False)
    op.create_index("ix_draft_pick_overall", "draft_pick", ["overall"], unique=False)
    op.create_index("ix_pick_year_round_overall", "draft_pick", ["year", "round", "overall"], unique=False)
    op.create_index("ix_pick_team_year", "draft_pick", ["team_id", "year"], unique=False)
    op.create_index("ix_draft_pick_team_id", "draft_pick", ["team_id"], unique=False)
    op.create_index("ix_draft_pick_player_id", "draft_pick", ["player_id"], unique=False)

    op.create_table(
        "player_season_stat",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("player.id"), nullable=False),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("team.id"), nullable=True),
        sa.Column("games", sa.Integer(), nullable=True),
        sa.Column("starts", sa.Integer(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.UniqueConstraint("player_id", "season", name="uq_player_season"),
    )
    op.create_index("ix_player_season_stat_player_id", "player_season_stat", ["player_id"], unique=False)
    op.create_index("ix_player_season_stat_season", "player_season_stat", ["season"], unique=False)
    op.create_index("ix_stat_player_season", "player_season_stat", ["player_id", "season"], unique=False)

    op.create_table(
        "pick_outcome",
        sa.Column("pick_id", sa.Integer(), sa.ForeignKey("draft_pick.id"), primary_key=True),
        sa.Column("outcome_score", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=16), nullable=False),
        sa.Column("method_version", sa.String(length=32), nullable=False, server_default="v1"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint("outcome_score >= 0 AND outcome_score <= 100", name="ck_outcome_score_0_100"),
    )
    op.create_index("ix_outcome_label", "pick_outcome", ["label"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_outcome_label", table_name="pick_outcome")
    op.drop_table("pick_outcome")

    op.drop_index("ix_stat_player_season", table_name="player_season_stat")
    op.drop_index("ix_player_season_stat_season", table_name="player_season_stat")
    op.drop_index("ix_player_season_stat_player_id", table_name="player_season_stat")
    op.drop_table("player_season_stat")

    op.drop_index("ix_draft_pick_player_id", table_name="draft_pick")
    op.drop_index("ix_draft_pick_team_id", table_name="draft_pick")
    op.drop_index("ix_pick_team_year", table_name="draft_pick")
    op.drop_index("ix_pick_year_round_overall", table_name="draft_pick")
    op.drop_index("ix_draft_pick_overall", table_name="draft_pick")
    op.drop_index("ix_draft_pick_round", table_name="draft_pick")
    op.drop_index("ix_draft_pick_year", table_name="draft_pick")
    op.drop_table("draft_pick")

    op.drop_index("ix_player_college", table_name="player")
    op.drop_index("ix_player_position", table_name="player")
    op.drop_index("ix_player_full_name", table_name="player")
    op.drop_table("player")

    op.drop_index("ix_team_abbrev", table_name="team")
    op.drop_table("team")
