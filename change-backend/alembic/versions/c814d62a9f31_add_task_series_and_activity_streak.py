"""add task series and daily activity streak fields

Revision ID: c814d62a9f31
Revises: b7e2c9d481a6
Create Date: 2026-09-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c814d62a9f31"
down_revision: Union[str, Sequence[str], None] = "b7e2c9d481a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "task_series",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("frequency", sa.String(length=20), nullable=False),
        sa.Column("interval", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("days_of_week", postgresql.ARRAY(sa.Integer()), nullable=False, server_default=sa.text("'{}'::integer[]")),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("local_time", sa.Time(), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="Africa/Lagos"),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("occurrence_limit", sa.Integer(), nullable=True),
        sa.Column("generated_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_task_series_user_active", "task_series", ["user_id", "is_active"])
    op.add_column("tasks", sa.Column("series_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("tasks", sa.Column("occurrence_date", sa.Date(), nullable=True))
    op.create_foreign_key(
        "fk_tasks_series_id_task_series", "tasks", "task_series", ["series_id"], ["id"], ondelete="SET NULL"
    )
    op.create_index("ix_tasks_series_id", "tasks", ["series_id"])
    op.create_index(
        "uq_tasks_series_occurrence_date",
        "tasks",
        ["series_id", "occurrence_date"],
        unique=True,
        postgresql_where=sa.text("series_id IS NOT NULL AND occurrence_date IS NOT NULL"),
    )
    op.add_column("users", sa.Column("current_streak", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("longest_streak", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("last_active_date", sa.Date(), nullable=True))
    op.add_column("users", sa.Column("last_active_timezone", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "last_active_timezone")
    op.drop_column("users", "last_active_date")
    op.drop_column("users", "longest_streak")
    op.drop_column("users", "current_streak")
    op.drop_index("uq_tasks_series_occurrence_date", table_name="tasks")
    op.drop_index("ix_tasks_series_id", table_name="tasks")
    op.drop_constraint("fk_tasks_series_id_task_series", "tasks", type_="foreignkey")
    op.drop_column("tasks", "occurrence_date")
    op.drop_column("tasks", "series_id")
    op.drop_index("ix_task_series_user_active", table_name="task_series")
    op.drop_table("task_series")
