from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0014_news_cache"
down_revision = "0013_matchup_stat"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "news_cache",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("items_json", sa.Text(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("news_cache")
