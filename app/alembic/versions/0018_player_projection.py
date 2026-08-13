from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0018_player_projection"
down_revision = "0017_player_injury"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "player_projection",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("week", sa.Integer(), nullable=True),  # NULL=ROS, 0=preseason, 1-18=that week
        sa.Column("gsis_id", sa.String(length=16), nullable=True),
        sa.Column("player_name", sa.String(length=128), nullable=False),
        sa.Column("team", sa.String(length=8), nullable=True),
        sa.Column("position", sa.String(length=8), nullable=False),
        sa.Column("points", sa.Float(), nullable=True),
        sa.Column("points_ppr", sa.Float(), nullable=True),
        sa.Column("points_half", sa.Float(), nullable=True),
        sa.Column("stats_json", sa.Text(), nullable=True),
    )
    op.create_index("ix_player_projection_season", "player_projection", ["season"], unique=False)
    op.create_index("ix_player_projection_gsis_id", "player_projection", ["gsis_id"], unique=False)
    op.create_index("ix_player_projection_player_name", "player_projection", ["player_name"], unique=False)
    op.create_index("ix_player_projection_position", "player_projection", ["position"], unique=False)
    op.create_index("ix_player_projection_season_week", "player_projection", ["season", "week"], unique=False)
    op.create_index(
        "ix_player_projection_season_week_position",
        "player_projection", ["season", "week", "position"], unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_player_projection_season_week_position", table_name="player_projection")
    op.drop_index("ix_player_projection_season_week", table_name="player_projection")
    op.drop_index("ix_player_projection_position", table_name="player_projection")
    op.drop_index("ix_player_projection_player_name", table_name="player_projection")
    op.drop_index("ix_player_projection_gsis_id", table_name="player_projection")
    op.drop_index("ix_player_projection_season", table_name="player_projection")
    op.drop_table("player_projection")
