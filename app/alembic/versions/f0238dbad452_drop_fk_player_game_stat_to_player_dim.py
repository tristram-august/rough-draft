"""drop fk player_game_stat to player_dim

Revision ID: f0238dbad452
Revises: 594be24f1f16
Create Date: 2026-03-29 00:44:53.789137
"""
from alembic import op
import sqlalchemy as sa

revision = 'f0238dbad452'
down_revision = '594be24f1f16'
branch_labels = None
depends_on = None


from alembic import op


def upgrade() -> None:
    # Drop FK that blocks historical ingest when player_dim is missing rows
    op.drop_constraint(
        "player_game_stat_player_gsis_id_fkey",
        "player_game_stat",
        type_="foreignkey",
    )


def downgrade() -> None:
    # Restore FK if you ever want strict integrity again
    op.create_foreign_key(
        "player_game_stat_player_gsis_id_fkey",
        source_table="player_game_stat",
        referent_table="player_dim",
        local_cols=["player_gsis_id"],
        remote_cols=["gsis_id"],
        ondelete=None,
    )
