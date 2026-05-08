from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0006_user_mod_flag"
down_revision = "0005_ol_season_stat"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user", sa.Column("is_mod", sa.Boolean(), nullable=False, server_default="false"))


def downgrade() -> None:
    op.drop_column("user", "is_mod")
