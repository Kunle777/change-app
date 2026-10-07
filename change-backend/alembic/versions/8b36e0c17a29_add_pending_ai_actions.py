"""add confirmation-gated AI task actions

Revision ID: 8b36e0c17a29
Revises: 2fa8c91d7e44
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "8b36e0c17a29"
down_revision: Union[str, Sequence[str], None] = "2fa8c91d7e44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pending_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tool_name", sa.String(length=50), nullable=False),
        sa.Column("summary", sa.String(length=300), nullable=False),
        sa.Column("arguments", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now() + interval '10 minutes'"),
        ),
        sa.ForeignKeyConstraint(["conversation_id"], ["ai_conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pending_actions_user_id", "pending_actions", ["user_id"])
    op.create_index("ix_pending_actions_conversation_id", "pending_actions", ["conversation_id"])
    op.add_column(
        "ai_interactions",
        sa.Column("pending_action_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_ai_interactions_pending_action_id_pending_actions",
        "ai_interactions",
        "pending_actions",
        ["pending_action_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_ai_interactions_pending_action_id", "ai_interactions", ["pending_action_id"])


def downgrade() -> None:
    op.drop_index("ix_ai_interactions_pending_action_id", table_name="ai_interactions")
    op.drop_constraint(
        "fk_ai_interactions_pending_action_id_pending_actions",
        "ai_interactions",
        type_="foreignkey",
    )
    op.drop_column("ai_interactions", "pending_action_id")
    op.drop_index("ix_pending_actions_conversation_id", table_name="pending_actions")
    op.drop_index("ix_pending_actions_user_id", table_name="pending_actions")
    op.drop_table("pending_actions")
