"""drop avatar_url and extend ai_interactions

Revision ID: a1b2c3d4e5f6
Revises: c5e6fd88af74
Create Date: 2026-08-08
"""
from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = ("c5e6fd88af74", "885645cfc9e4")


def upgrade():
    op.drop_column("users", "avatar_url")

    op.create_table(
        "ai_interactions",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("message", sa.String, nullable=False),
        sa.Column("response", sa.String, nullable=True),
        sa.Column("intent", sa.String, nullable=True),
        sa.Column("context_size", sa.Integer, nullable=True),
        sa.Column("tool_used", sa.Boolean, server_default="false"),
        sa.Column("tool_name", sa.String, nullable=True),
        sa.Column("input_tokens", sa.Integer, nullable=True),
        sa.Column("output_tokens", sa.Integer, nullable=True),
        sa.Column("status", sa.String, server_default="success"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.add_column("users", sa.Column("avatar_url", sa.String, nullable=True))
    op.drop_table("ai_interactions")
