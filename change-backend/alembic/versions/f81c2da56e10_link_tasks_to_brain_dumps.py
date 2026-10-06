"""link created tasks to their source brain dump

Revision ID: f81c2da56e10
Revises: 31f531df0730
Create Date: 2026-09-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f81c2da56e10"
down_revision: Union[str, Sequence[str], None] = "31f531df0730"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("source_brain_dump_id", sa.UUID(), nullable=True))
    op.create_index(
        "ix_tasks_source_brain_dump_id", "tasks", ["source_brain_dump_id"]
    )
    op.create_foreign_key(
        "fk_tasks_source_brain_dump_id_brain_dumps",
        "tasks",
        "brain_dumps",
        ["source_brain_dump_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_tasks_source_brain_dump_id_brain_dumps", "tasks", type_="foreignkey"
    )
    op.drop_index("ix_tasks_source_brain_dump_id", table_name="tasks")
    op.drop_column("tasks", "source_brain_dump_id")
