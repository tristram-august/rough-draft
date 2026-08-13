from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0017_player_injury"
down_revision = "0016_post_social"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # gsis_id is the primary key, not a surrogate id -- this table is exactly
    # "one row per currently-injured, linkable player," rebuilt from scratch
    # on every ingest run (see PlayerInjury docstring). No FK to player_dim,
    # matching fantasy_rank.gsis_id's established no-FK precedent.
    op.create_table(
        "player_injury",
        sa.Column("gsis_id", sa.String(length=16), primary_key=True),
        sa.Column("player_name", sa.String(length=128), nullable=False),
        sa.Column("team", sa.String(length=8), nullable=True),
        sa.Column("position", sa.String(length=8), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("status_short", sa.String(length=8), nullable=True),
        sa.Column("injury_type", sa.String(length=64), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("probability_of_playing", sa.String(length=16), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_player_injury_status", "player_injury", ["status"], unique=False)
    op.create_index("ix_player_injury_position", "player_injury", ["position"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_player_injury_position", table_name="player_injury")
    op.drop_index("ix_player_injury_status", table_name="player_injury")
    op.drop_table("player_injury")
