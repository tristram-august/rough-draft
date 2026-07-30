from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0012_power_ranking"
down_revision = "0011_game_pick"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "power_ranking",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("subject_type", sa.String(16), nullable=False),
        sa.Column("subject_group", sa.String(16), nullable=False, server_default=""),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("week", sa.Integer(), nullable=True),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("is_official", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "subject_type", "subject_group", "season", "week", "author_id",
            name="uq_power_ranking_ballot",
        ),
    )
    op.create_index("ix_power_ranking_subject_type", "power_ranking", ["subject_type"])
    op.create_index("ix_power_ranking_season", "power_ranking", ["season"])
    op.create_index("ix_power_ranking_week", "power_ranking", ["week"])
    op.create_index("ix_power_ranking_author_id", "power_ranking", ["author_id"])
    op.create_index(
        "ix_power_scope", "power_ranking", ["subject_type", "subject_group", "season", "week"]
    )

    op.create_table(
        "power_ranking_entry",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "ranking_id",
            sa.Integer(),
            sa.ForeignKey("power_ranking.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("subject_id", sa.String(32), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.UniqueConstraint("ranking_id", "rank", name="uq_power_entry_rank"),
        sa.UniqueConstraint("ranking_id", "subject_id", name="uq_power_entry_subject"),
    )
    op.create_index("ix_power_entry_ranking_id", "power_ranking_entry", ["ranking_id"])
    op.create_index("ix_power_entry_subject_id", "power_ranking_entry", ["subject_id"])


def downgrade() -> None:
    op.drop_index("ix_power_entry_subject_id", "power_ranking_entry")
    op.drop_index("ix_power_entry_ranking_id", "power_ranking_entry")
    op.drop_table("power_ranking_entry")
    op.drop_index("ix_power_scope", "power_ranking")
    op.drop_index("ix_power_ranking_author_id", "power_ranking")
    op.drop_index("ix_power_ranking_week", "power_ranking")
    op.drop_index("ix_power_ranking_season", "power_ranking")
    op.drop_index("ix_power_ranking_subject_type", "power_ranking")
    op.drop_table("power_ranking")
