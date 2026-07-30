from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0009_game"
down_revision = "0008_blog"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "game",
        sa.Column("game_id", sa.String(32), primary_key=True),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("game_type", sa.String(8), nullable=True),
        sa.Column("week", sa.Integer(), nullable=True),
        sa.Column("gameday", sa.Date(), nullable=True),
        sa.Column("weekday", sa.String(12), nullable=True),
        sa.Column("gametime", sa.String(8), nullable=True),
        sa.Column("away_team", sa.String(8), nullable=False),
        sa.Column("home_team", sa.String(8), nullable=False),
        sa.Column("away_score", sa.Integer(), nullable=True),
        sa.Column("home_score", sa.Integer(), nullable=True),
        sa.Column("result", sa.Float(), nullable=True),
        sa.Column("overtime", sa.Boolean(), nullable=True),
        sa.Column("spread_line", sa.Float(), nullable=True),
        sa.Column("total_line", sa.Float(), nullable=True),
        sa.Column("div_game", sa.Boolean(), nullable=True),
        sa.Column("roof", sa.String(16), nullable=True),
        sa.Column("surface", sa.String(24), nullable=True),
        sa.Column("stadium", sa.String(64), nullable=True),
        sa.Column("location", sa.String(16), nullable=True),
        sa.Column("away_qb_name", sa.String(64), nullable=True),
        sa.Column("home_qb_name", sa.String(64), nullable=True),
        sa.Column("away_coach", sa.String(64), nullable=True),
        sa.Column("home_coach", sa.String(64), nullable=True),
    )
    op.create_index("ix_game_season", "game", ["season"])
    op.create_index("ix_game_week", "game", ["week"])
    op.create_index("ix_game_away_team", "game", ["away_team"])
    op.create_index("ix_game_home_team", "game", ["home_team"])
    op.create_index("ix_game_season_week", "game", ["season", "week"])
    op.create_index("ix_game_gameday", "game", ["gameday"])


def downgrade() -> None:
    op.drop_index("ix_game_gameday", "game")
    op.drop_index("ix_game_season_week", "game")
    op.drop_index("ix_game_home_team", "game")
    op.drop_index("ix_game_away_team", "game")
    op.drop_index("ix_game_week", "game")
    op.drop_index("ix_game_season", "game")
    op.drop_table("game")
