from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0008_blog"
down_revision = "0007_email_verification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "post",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(160), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("subtitle", sa.String(300), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("body_markdown", sa.Text(), nullable=False, server_default=""),
        sa.Column("cover_image_url", sa.Text(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('draft', 'published')", name="ck_post_status"),
    )
    op.create_index("ix_post_slug", "post", ["slug"], unique=True)
    op.create_index("ix_post_author_id", "post", ["author_id"])
    op.create_index("ix_post_status_published", "post", ["status", "published_at"])

    op.create_table(
        "post_tag",
        sa.Column("post_id", sa.Integer(), sa.ForeignKey("post.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag", sa.String(32), primary_key=True),
    )
    op.create_index("ix_post_tag_tag", "post_tag", ["tag"])


def downgrade() -> None:
    op.drop_index("ix_post_tag_tag", "post_tag")
    op.drop_table("post_tag")
    op.drop_index("ix_post_status_published", "post")
    op.drop_index("ix_post_author_id", "post")
    op.drop_index("ix_post_slug", "post")
    op.drop_table("post")
