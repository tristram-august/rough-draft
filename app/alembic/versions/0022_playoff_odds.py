from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0022_playoff_odds"
down_revision = "0021_team_game_stat_detail"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "playoff_odds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("week", sa.Integer(), nullable=False),
        sa.Column("team", sa.String(8), nullable=False),
        sa.Column("elo", sa.Float(), nullable=False),
        sa.Column("wins", sa.Float(), nullable=False),
        sa.Column("losses", sa.Float(), nullable=False),
        sa.Column("mean_wins", sa.Float(), nullable=False),
        sa.Column("make_playoffs", sa.Float(), nullable=False),
        sa.Column("win_division", sa.Float(), nullable=False),
        sa.Column("first_seed", sa.Float(), nullable=False),
        sa.Column("win_conference", sa.Float(), nullable=False),
        sa.Column("win_super_bowl", sa.Float(), nullable=False),
        sa.Column("seed_probs", sa.Text(), nullable=False),
        sa.Column("sims", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("season", "week", "team", name="uq_playoff_odds"),
    )
    op.create_index("ix_playoff_odds_season_week", "playoff_odds", ["season", "week"])
    op.create_table(
        "playoff_calibration",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bucket_lo", sa.Float(), nullable=False),
        sa.Column("bucket_hi", sa.Float(), nullable=False),
        sa.Column("n", sa.Integer(), nullable=False),
        sa.Column("predicted", sa.Float(), nullable=False),
        sa.Column("actual", sa.Float(), nullable=False),
        sa.Column("seasons", sa.String(32), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("playoff_calibration")
    op.drop_index("ix_playoff_odds_season_week", table_name="playoff_odds")
    op.drop_table("playoff_odds")
