"""add priority reminders and finalize AI and entitlement schema

Revision ID: 5ef74f73add1
Revises: a1b2c3d4e5f6
Create Date: 2026-09-21 23:13:41.189527
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '5ef74f73add1'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Priority Reminder ---
    op.add_column(
        "tasks",
        sa.Column("priority_reminder", sa.Boolean, nullable=False, server_default=sa.false()),
    )

    # --- feature_entitlements.user_id must be unique ---
    op.create_unique_constraint(
        "uq_feature_entitlements_user_id", "feature_entitlements", ["user_id"]
    )

    # --- Evolve ai_interactions to final schema ---
    op.alter_column("ai_interactions", "message", new_column_name="question")
    op.alter_column("ai_interactions", "response", existing_type=sa.String, type_=sa.Text, nullable=False)
    op.alter_column("ai_interactions", "question", existing_type=sa.String, type_=sa.Text, nullable=False)
    op.add_column("ai_interactions", sa.Column("context_used", sa.Text, nullable=True))
    op.add_column("ai_interactions", sa.Column("was_helpful", sa.Boolean, nullable=True))


def downgrade() -> None:
    op.drop_column("ai_interactions", "was_helpful")
    op.drop_column("ai_interactions", "context_used")
    op.alter_column("ai_interactions", "question", existing_type=sa.Text, type_=sa.String, nullable=True)
    op.alter_column("ai_interactions", "response", existing_type=sa.Text, type_=sa.String, nullable=True)
    op.alter_column("ai_interactions", "question", new_column_name="message")
    op.drop_constraint("uq_feature_entitlements_user_id", "feature_entitlements", type_="unique")
    op.drop_column("tasks", "priority_reminder")
