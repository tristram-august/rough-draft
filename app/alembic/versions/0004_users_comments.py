from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0004_users_comments"
down_revision = "d8ed25393ef5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=32), nullable=False),
        sa.Column("email", sa.String(length=128), nullable=False),
        sa.Column("hashed_password", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("username", name="uq_user_username"),
        sa.UniqueConstraint("email", name="uq_user_email"),
    )
    op.create_index("ix_user_username", "user", ["username"], unique=True)
    op.create_index("ix_user_email", "user", ["email"], unique=True)

    op.create_table(
        "comment",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pick_id", sa.Integer(), sa.ForeignKey("draft_pick.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("char_length(body) >= 1", name="ck_comment_body_not_empty"),
    )
    op.create_index("ix_comment_pick_id", "comment", ["pick_id"], unique=False)
    op.create_index("ix_comment_user_id", "comment", ["user_id"], unique=False)
    op.create_index("ix_comment_pick_created", "comment", ["pick_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_comment_pick_created", table_name="comment")
    op.drop_index("ix_comment_user_id", table_name="comment")
    op.drop_index("ix_comment_pick_id", table_name="comment")
    op.drop_table("comment")

    op.drop_index("ix_user_email", table_name="user")
    op.drop_index("ix_user_username", table_name="user")
    op.drop_table("user")
