from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0002_votes"
down_revision = "0001_init"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "pick_vote",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pick_id", sa.Integer(), sa.ForeignKey("draft_pick.id"), nullable=False),
        sa.Column("voter_type", sa.String(length=8), nullable=False),
        sa.Column("voter_key", sa.String(length=64), nullable=False),
        sa.Column("value", sa.String(length=8), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("pick_id", "voter_type", "voter_key", name="uq_vote_one_per_voter_per_pick"),
    )
    op.create_index("ix_vote_pick_value", "pick_vote", ["pick_id", "value"], unique=False)
    op.create_index("ix_pick_vote_pick_id", "pick_vote", ["pick_id"], unique=False)

def downgrade() -> None:
    op.drop_index("ix_pick_vote_pick_id", table_name="pick_vote")
    op.drop_index("ix_vote_pick_value", table_name="pick_vote")
    op.drop_table("pick_vote")
