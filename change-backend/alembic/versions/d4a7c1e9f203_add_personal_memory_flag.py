"""add users.personal_memory_enabled (opt-in personal memory consent)

Revision ID: d4a7c1e9f203
Revises: 7c9d1a4e6f20
"""

from alembic import op
import sqlalchemy as sa


revision = "d4a7c1e9f203"
down_revision = "7c9d1a4e6f20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("personal_memory_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("users", "personal_memory_enabled")
