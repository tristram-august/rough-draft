from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0003_career_summary"
down_revision = "0002_votes"  # adjust if your last revision differs
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "player_career_summary",
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("player.id"), primary_key=True),

        sa.Column("gsis_id", sa.String(length=16), nullable=True),
        sa.Column("pfr_player_id", sa.String(length=32), nullable=True),
        sa.Column("cfb_player_id", sa.Integer(), nullable=True),

        sa.Column("hof", sa.Boolean(), nullable=True),
        sa.Column("allpro", sa.Integer(), nullable=True),
        sa.Column("probowls", sa.Integer(), nullable=True),
        sa.Column("seasons_started", sa.Integer(), nullable=True),

        sa.Column("w_av", sa.Float(), nullable=True),
        sa.Column("car_av", sa.Float(), nullable=True),
        sa.Column("dr_av", sa.Float(), nullable=True),

        sa.Column("games", sa.Integer(), nullable=True),

        sa.Column("pass_completions", sa.Integer(), nullable=True),
        sa.Column("pass_attempts", sa.Integer(), nullable=True),
        sa.Column("pass_yards", sa.Integer(), nullable=True),
        sa.Column("pass_tds", sa.Integer(), nullable=True),
        sa.Column("pass_ints", sa.Integer(), nullable=True),

        sa.Column("rush_atts", sa.Integer(), nullable=True),
        sa.Column("rush_yards", sa.Integer(), nullable=True),
        sa.Column("rush_tds", sa.Integer(), nullable=True),

        sa.Column("receptions", sa.Integer(), nullable=True),
        sa.Column("rec_yards", sa.Integer(), nullable=True),
        sa.Column("rec_tds", sa.Integer(), nullable=True),

        sa.Column("def_solo_tackles", sa.Integer(), nullable=True),
        sa.Column("def_ints", sa.Integer(), nullable=True),
        sa.Column("def_sacks", sa.Float(), nullable=True),
    )
    op.create_index("ix_career_gsis_id", "player_career_summary", ["gsis_id"], unique=False)
    op.create_index("ix_career_pfr_player_id", "player_career_summary", ["pfr_player_id"], unique=False)
    op.create_index("ix_career_cfb_player_id", "player_career_summary", ["cfb_player_id"], unique=False)

def downgrade() -> None:
    op.drop_index("ix_career_cfb_player_id", table_name="player_career_summary")
    op.drop_index("ix_career_pfr_player_id", table_name="player_career_summary")
    op.drop_index("ix_career_gsis_id", table_name="player_career_summary")
    op.drop_table("player_career_summary")
