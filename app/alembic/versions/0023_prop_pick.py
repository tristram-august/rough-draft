from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0023_prop_pick"
down_revision = "0022_playoff_odds"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prop_pick",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("week", sa.Integer(), nullable=False),
        sa.Column("gsis_id", sa.String(16), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("position", sa.String(8), nullable=False),
        sa.Column("team", sa.String(8), nullable=False),
        sa.Column("opponent", sa.String(8), nullable=False),
        sa.Column("stat", sa.String(24), nullable=False),
        sa.Column("line", sa.Float(), nullable=False),
        sa.Column("projection", sa.Float(), nullable=False),
        sa.Column("p_over", sa.Float(), nullable=False),
        sa.Column("mean", sa.Float(), nullable=False),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actual", sa.Float(), nullable=True),
        sa.Column("result", sa.String(8), nullable=True),
        sa.Column("graded_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("season", "week", "gsis_id", "stat", name="uq_prop_pick"),
    )
    op.create_index("ix_prop_pick_season_week", "prop_pick", ["season", "week"])


def downgrade() -> None:
    op.drop_index("ix_prop_pick_season_week", table_name="prop_pick")
    op.drop_table("prop_pick")
