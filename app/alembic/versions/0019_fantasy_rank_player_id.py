from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0019_fantasy_rank_player_id"
down_revision = "0018_player_projection"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No backfill needed -- fantasy_rank is fully delete-then-rebuilt on every
    # ingest_fantasypros.py run, so the next scheduled ingest populates this.
    op.add_column("fantasy_rank", sa.Column("fantasypros_player_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("fantasy_rank", "fantasypros_player_id")
