"""add AI conversations and link chat interactions

Revision ID: 2fa8c91d7e44
Revises: f3a1b7c9d204
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "2fa8c91d7e44"
down_revision: Union[str, Sequence[str], None] = "f3a1b7c9d204"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_conversations_user_id", "ai_conversations", ["user_id"])
    op.create_index("ix_ai_conversations_updated_at", "ai_conversations", ["updated_at"])
    op.add_column(
        "ai_interactions",
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_ai_interactions_conversation_id_ai_conversations",
        "ai_interactions",
        "ai_conversations",
        ["conversation_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_ai_interactions_conversation_id", "ai_interactions", ["conversation_id"])


def downgrade() -> None:
    op.drop_index("ix_ai_interactions_conversation_id", table_name="ai_interactions")
    op.drop_constraint(
        "fk_ai_interactions_conversation_id_ai_conversations",
        "ai_interactions",
        type_="foreignkey",
    )
    op.drop_column("ai_interactions", "conversation_id")
    op.drop_index("ix_ai_conversations_updated_at", table_name="ai_conversations")
    op.drop_index("ix_ai_conversations_user_id", table_name="ai_conversations")
    op.drop_table("ai_conversations")
