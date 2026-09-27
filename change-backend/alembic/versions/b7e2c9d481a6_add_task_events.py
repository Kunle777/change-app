"""add task event log, durable outbox, and join migration heads

Revision ID: b7e2c9d481a6
Revises: f81c2da56e10, 885645cfc9e4
Create Date: 2026-09-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b7e2c9d481a6"
down_revision: Union[str, Sequence[str], None] = ("f81c2da56e10", "885645cfc9e4")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "task_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(length=30), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "event_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_task_events_user_id", "task_events", ["user_id"])
    op.create_index("ix_task_events_task_id", "task_events", ["task_id"])
    op.create_index(
        "ix_task_events_user_occurred_at",
        "task_events",
        ["user_id", "occurred_at"],
    )
    op.create_index(
        "uq_task_events_overdue_deadline",
        "task_events",
        ["task_id", sa.text("(event_metadata->>'due_date')")],
        unique=True,
        postgresql_where=sa.text("event_type = 'overdue' AND task_id IS NOT NULL"),
    )
    op.create_index(
        "uq_task_events_reminder_open_notification",
        "task_events",
        ["task_id", sa.text("(event_metadata->>'notification_id')")],
        unique=True,
        postgresql_where=sa.text("event_type = 'reminder_opened' AND task_id IS NOT NULL"),
    )
    op.create_index(
        "uq_task_events_reminder_scheduled_notification",
        "task_events",
        ["task_id", sa.text("(event_metadata->>'notification_id')")],
        unique=True,
        postgresql_where=sa.text("event_type = 'reminder_scheduled' AND task_id IS NOT NULL"),
    )

    op.create_table(
        "task_event_outbox",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(length=30), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "event_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.String(length=100), nullable=True),
    )
    op.create_index("ix_task_event_outbox_user_id", "task_event_outbox", ["user_id"])
    op.create_index("ix_task_event_outbox_created_at", "task_event_outbox", ["created_at"])
    op.create_index(
        "uq_task_event_outbox_overdue_deadline",
        "task_event_outbox",
        ["task_id", sa.text("(event_metadata->>'due_date')")],
        unique=True,
        postgresql_where=sa.text("event_type = 'overdue' AND task_id IS NOT NULL"),
    )
    op.create_index(
        "uq_task_event_outbox_reminder_open_notification",
        "task_event_outbox",
        ["task_id", sa.text("(event_metadata->>'notification_id')")],
        unique=True,
        postgresql_where=sa.text("event_type = 'reminder_opened' AND task_id IS NOT NULL"),
    )
    op.create_index(
        "uq_task_event_outbox_reminder_scheduled_notification",
        "task_event_outbox",
        ["task_id", sa.text("(event_metadata->>'notification_id')")],
        unique=True,
        postgresql_where=sa.text("event_type = 'reminder_scheduled' AND task_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_task_event_outbox_reminder_scheduled_notification", table_name="task_event_outbox")
    op.drop_index("uq_task_event_outbox_reminder_open_notification", table_name="task_event_outbox")
    op.drop_index("uq_task_event_outbox_overdue_deadline", table_name="task_event_outbox")
    op.drop_index("ix_task_event_outbox_created_at", table_name="task_event_outbox")
    op.drop_index("ix_task_event_outbox_user_id", table_name="task_event_outbox")
    op.drop_table("task_event_outbox")
    op.drop_index("uq_task_events_reminder_scheduled_notification", table_name="task_events")
    op.drop_index("uq_task_events_reminder_open_notification", table_name="task_events")
    op.drop_index("uq_task_events_overdue_deadline", table_name="task_events")
    op.drop_index("ix_task_events_user_occurred_at", table_name="task_events")
    op.drop_index("ix_task_events_task_id", table_name="task_events")
    op.drop_index("ix_task_events_user_id", table_name="task_events")
    op.drop_table("task_events")
