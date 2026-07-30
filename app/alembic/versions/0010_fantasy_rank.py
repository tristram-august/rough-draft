from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0010_fantasy_rank"
down_revision = "0009_game"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fantasy_rank",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("overall_rank", sa.Integer(), nullable=False),
        sa.Column("tier", sa.Integer(), nullable=True),
        sa.Column("player_name", sa.String(128), nullable=False),
        sa.Column("team", sa.String(8), nullable=True),
        sa.Column("position", sa.String(8), nullable=False),
        sa.Column("position_rank", sa.Integer(), nullable=True),
        sa.Column("bye_week", sa.Integer(), nullable=True),
        sa.Column("sos", sa.Integer(), nullable=True),
        sa.Column("ecr_vs_adp", sa.Integer(), nullable=True),
        sa.Column("avg_diff", sa.Float(), nullable=True),
        sa.Column("gsis_id", sa.String(16), nullable=True),
        sa.UniqueConstraint("season", "overall_rank", name="uq_fantasy_rank_season_rank"),
    )
    op.create_index("ix_fantasy_rank_season", "fantasy_rank", ["season"])
    op.create_index("ix_fantasy_rank_player_name", "fantasy_rank", ["player_name"])
    op.create_index("ix_fantasy_rank_position", "fantasy_rank", ["position"])
    op.create_index("ix_fantasy_rank_gsis_id", "fantasy_rank", ["gsis_id"])
    op.create_index("ix_fantasy_rank_season_pos", "fantasy_rank", ["season", "position"])


def downgrade() -> None:
    op.drop_index("ix_fantasy_rank_season_pos", "fantasy_rank")
    op.drop_index("ix_fantasy_rank_gsis_id", "fantasy_rank")
    op.drop_index("ix_fantasy_rank_position", "fantasy_rank")
    op.drop_index("ix_fantasy_rank_player_name", "fantasy_rank")
    op.drop_index("ix_fantasy_rank_season", "fantasy_rank")
    op.drop_table("fantasy_rank")
