from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0013_matchup_stat"
down_revision = "0012_power_ranking"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "matchup_stat",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("game_id", sa.String(32), sa.ForeignKey("game.game_id"), nullable=False),
        sa.Column("category", sa.String(16), nullable=False),
        sa.Column("stat_label", sa.String(64), nullable=False),
        sa.Column("team", sa.String(8), nullable=False),
        sa.Column("team_value", sa.String(24), nullable=False),
        sa.Column("team_rank", sa.Integer(), nullable=True),
        sa.Column("opp_team", sa.String(8), nullable=False),
        sa.Column("opp_stat_label", sa.String(64), nullable=False),
        sa.Column("opp_value", sa.String(24), nullable=False),
        sa.Column("opp_rank", sa.Integer(), nullable=True),
        sa.Column("source_season", sa.Integer(), nullable=False),
        sa.UniqueConstraint("game_id", "category", "stat_label", "team", name="uq_matchup_stat_row"),
    )
    op.create_index("ix_matchup_stat_game_id", "matchup_stat", ["game_id"])
    op.create_index("ix_matchup_stat_category", "matchup_stat", ["category"])


def downgrade() -> None:
    op.drop_index("ix_matchup_stat_category", "matchup_stat")
    op.drop_index("ix_matchup_stat_game_id", "matchup_stat")
    op.drop_table("matchup_stat")
