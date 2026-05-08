from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0005_ol_season_stat"
down_revision = "0004_users_comments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ol_season_stat",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("player.id"), nullable=False),
        sa.Column("pff_player_id", sa.Integer(), nullable=True),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("position", sa.String(4), nullable=True),
        sa.Column("team_abbrev", sa.String(8), nullable=True),
        sa.Column("games", sa.Integer(), nullable=True),
        sa.Column("snap_counts_offense", sa.Integer(), nullable=True),
        sa.Column("pressures_allowed", sa.Integer(), nullable=True),
        sa.Column("hurries_allowed", sa.Integer(), nullable=True),
        sa.Column("hits_allowed", sa.Integer(), nullable=True),
        sa.Column("sacks_allowed", sa.Integer(), nullable=True),
        sa.Column("pbe", sa.Float(), nullable=True),
        sa.Column("pass_block_percent", sa.Float(), nullable=True),
        sa.Column("penalties", sa.Integer(), nullable=True),
    )
    op.create_index("ix_ol_player_id", "ol_season_stat", ["player_id"])
    op.create_index("ix_ol_pff_player_id", "ol_season_stat", ["pff_player_id"])
    op.create_index("ix_ol_season", "ol_season_stat", ["season"])
    op.create_unique_constraint("uq_ol_player_season", "ol_season_stat", ["player_id", "season"])


def downgrade() -> None:
    op.drop_table("ol_season_stat")
