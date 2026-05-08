from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0007_email_verification"
down_revision = "0006_user_mod_flag"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user", sa.Column("email_verified", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("user", sa.Column("verify_token", sa.String(64), nullable=True))
    op.add_column("user", sa.Column("reset_token", sa.String(64), nullable=True))
    op.add_column("user", sa.Column("reset_token_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_user_verify_token", "user", ["verify_token"])
    op.create_index("ix_user_reset_token", "user", ["reset_token"])


def downgrade() -> None:
    op.drop_index("ix_user_reset_token", "user")
    op.drop_index("ix_user_verify_token", "user")
    op.drop_column("user", "reset_token_expires_at")
    op.drop_column("user", "reset_token")
    op.drop_column("user", "verify_token")
    op.drop_column("user", "email_verified")
