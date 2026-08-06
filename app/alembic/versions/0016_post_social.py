from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0016_post_social"
down_revision = "0015_elo_predictions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # post_id cascades on Post deletion (unlike comment.pick_id / pick_vote.pick_id,
    # which never needed it since DraftPick rows are never deleted) because Post
    # rows ARE deletable via DELETE /posts/{post_id}, and PostTag already relies on
    # the same cascade so a post delete doesn't leave orphaned rows behind.
    op.create_table(
        "post_comment",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("post_id", sa.Integer(), sa.ForeignKey("post.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("char_length(body) >= 1", name="ck_post_comment_body_not_empty"),
    )
    op.create_index("ix_post_comment_post_id", "post_comment", ["post_id"], unique=False)
    op.create_index("ix_post_comment_user_id", "post_comment", ["user_id"], unique=False)
    op.create_index("ix_post_comment_post_created", "post_comment", ["post_id", "created_at"], unique=False)

    op.create_table(
        "post_like",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("post_id", sa.Integer(), sa.ForeignKey("post.id", ondelete="CASCADE"), nullable=False),
        sa.Column("liker_type", sa.String(length=8), nullable=False),
        sa.Column("liker_key", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("post_id", "liker_type", "liker_key", name="uq_like_one_per_liker_per_post"),
    )
    op.create_index("ix_post_like_post_id", "post_like", ["post_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_post_like_post_id", table_name="post_like")
    op.drop_table("post_like")

    op.drop_index("ix_post_comment_post_created", table_name="post_comment")
    op.drop_index("ix_post_comment_user_id", table_name="post_comment")
    op.drop_index("ix_post_comment_post_id", table_name="post_comment")
    op.drop_table("post_comment")
