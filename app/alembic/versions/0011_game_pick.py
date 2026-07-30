from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0011_game_pick"
down_revision = "0010_fantasy_rank"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "game_pick",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("game_id", sa.String(32), sa.ForeignKey("game.game_id"), nullable=False),
        sa.Column("voter_type", sa.String(8), nullable=False),
        sa.Column("voter_key", sa.String(64), nullable=False),
        sa.Column("picked_team", sa.String(8), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "game_id", "voter_type", "voter_key", name="uq_pick_one_per_voter_per_game"
        ),
    )
    op.create_index("ix_game_pick_game_id", "game_pick", ["game_id"])
    op.create_index("ix_game_pick_voter", "game_pick", ["voter_type", "voter_key"])


def downgrade() -> None:
    op.drop_index("ix_game_pick_voter", "game_pick")
    op.drop_index("ix_game_pick_game_id", "game_pick")
    op.drop_table("game_pick")
