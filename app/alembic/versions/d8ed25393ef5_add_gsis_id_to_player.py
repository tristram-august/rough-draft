"""add gsis_id to player

Revision ID: d8ed25393ef5
Revises: f0238dbad452
Create Date: 2026-03-29 01:30:37.426608
"""
from alembic import op
import sqlalchemy as sa

revision = 'd8ed25393ef5'
down_revision = 'f0238dbad452'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("player", sa.Column("gsis_id", sa.String(length=16), nullable=True))
    op.create_index("ix_player_gsis_id", "player", ["gsis_id"])


def downgrade() -> None:
    op.drop_index("ix_player_gsis_id", table_name="player")
    op.drop_column("player", "gsis_id")
