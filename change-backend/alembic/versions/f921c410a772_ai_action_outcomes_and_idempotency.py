"""persist AI action outcomes and chat idempotency keys

Revision ID: f921c410a772
Revises: d4a7c1e9f203
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f921c410a772"
down_revision: Union[str, Sequence[str], None] = "d4a7c1e9f203"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "pending_actions",
        sa.Column("outcome", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "ai_interactions",
        sa.Column("idempotency_key", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "ai_interactions",
        sa.Column("resolved_action_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "ai_interactions",
        sa.Column("resolved_action_status", sa.String(length=20), nullable=True),
    )
    op.create_foreign_key(
        "fk_ai_interactions_resolved_action_id_pending_actions",
        "ai_interactions",
        "pending_actions",
        ["resolved_action_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_unique_constraint(
        "uq_ai_interactions_user_idempotency",
        "ai_interactions",
        ["user_id", "idempotency_key"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_ai_interactions_resolved_action_id_pending_actions",
        "ai_interactions",
        type_="foreignkey",
    )
    op.drop_column("ai_interactions", "resolved_action_status")
    op.drop_column("ai_interactions", "resolved_action_id")
    op.drop_constraint(
        "uq_ai_interactions_user_idempotency",
        "ai_interactions",
        type_="unique",
    )
    op.drop_column("ai_interactions", "idempotency_key")
    op.drop_column("pending_actions", "outcome")
