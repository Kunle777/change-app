"""add context_richness to ai_interactions

Revision ID: a2c4e6f8b1d3
Revises: a1b2c3d4e5f6
Create Date: 2026-09-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "a2c4e6f8b1d3"
down_revision = "c814f9a1d70e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ai_interactions",
        sa.Column("context_richness", sa.String(20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ai_interactions", "context_richness")
