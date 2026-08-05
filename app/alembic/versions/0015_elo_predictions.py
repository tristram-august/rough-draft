from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0015_elo_predictions"
down_revision = "0014_news_cache"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "elo_rating",
        sa.Column("team", sa.String(8), primary_key=True),
        sa.Column("rating", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "game_prediction",
        sa.Column("game_id", sa.String(32), sa.ForeignKey("game.game_id"), primary_key=True),
        sa.Column("home_elo_pre", sa.Float(), nullable=False),
        sa.Column("away_elo_pre", sa.Float(), nullable=False),
        sa.Column("home_win_prob", sa.Float(), nullable=False),
        sa.Column("predicted_winner", sa.String(8), nullable=False),
        sa.Column("actual_winner", sa.String(8), nullable=True),
        sa.Column("correct", sa.Boolean(), nullable=True),
        sa.Column("vegas_favorite", sa.String(8), nullable=True),
        sa.Column("vegas_correct", sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("game_prediction")
    op.drop_table("elo_rating")
