from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0020_team_game_stat"
down_revision = "0019_fantasy_rank_player_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "team_game_stat",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("week", sa.Integer(), nullable=True),
        sa.Column("season_type", sa.String(8), nullable=True),
        sa.Column("game_id", sa.String(32), nullable=False),
        sa.Column("team", sa.String(8), nullable=False),
        sa.Column("opponent_team", sa.String(8), nullable=True),
        sa.Column("completions", sa.Integer(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=True),
        sa.Column("passing_yards", sa.Integer(), nullable=True),
        sa.Column("passing_tds", sa.Integer(), nullable=True),
        sa.Column("passing_interceptions", sa.Integer(), nullable=True),
        sa.Column("passing_epa", sa.Float(), nullable=True),
        sa.Column("passing_cpoe", sa.Float(), nullable=True),
        sa.Column("carries", sa.Integer(), nullable=True),
        sa.Column("rushing_yards", sa.Integer(), nullable=True),
        sa.Column("rushing_tds", sa.Integer(), nullable=True),
        sa.Column("rushing_epa", sa.Float(), nullable=True),
        sa.Column("receptions", sa.Integer(), nullable=True),
        sa.Column("targets", sa.Integer(), nullable=True),
        sa.Column("receiving_yards", sa.Integer(), nullable=True),
        sa.Column("receiving_tds", sa.Integer(), nullable=True),
        sa.Column("receiving_epa", sa.Float(), nullable=True),
        sa.Column("sack_fumbles_lost", sa.Integer(), nullable=True),
        sa.Column("rushing_fumbles_lost", sa.Integer(), nullable=True),
        sa.Column("receiving_fumbles_lost", sa.Integer(), nullable=True),
        sa.Column("def_tackles_for_loss", sa.Integer(), nullable=True),
        sa.Column("def_fumbles_forced", sa.Integer(), nullable=True),
        sa.Column("def_sacks", sa.Float(), nullable=True),
        sa.Column("def_qb_hits", sa.Integer(), nullable=True),
        sa.Column("def_interceptions", sa.Integer(), nullable=True),
        sa.Column("def_tds", sa.Integer(), nullable=True),
        sa.Column("fg_made", sa.Integer(), nullable=True),
        sa.Column("fg_att", sa.Integer(), nullable=True),
        sa.Column("pat_made", sa.Integer(), nullable=True),
        sa.Column("pat_att", sa.Integer(), nullable=True),
        sa.Column("penalties", sa.Integer(), nullable=True),
        sa.Column("penalty_yards", sa.Integer(), nullable=True),
        sa.UniqueConstraint("game_id", "team", name="uq_team_game"),
    )
    op.create_index("ix_tgs_season_week", "team_game_stat", ["season", "week"])
    op.create_index("ix_tgs_team_season", "team_game_stat", ["team", "season"])
    op.create_index("ix_tgs_season", "team_game_stat", ["season"])
    op.create_index("ix_tgs_game_id", "team_game_stat", ["game_id"])
    op.create_index("ix_tgs_team", "team_game_stat", ["team"])


def downgrade() -> None:
    op.drop_table("team_game_stat")
