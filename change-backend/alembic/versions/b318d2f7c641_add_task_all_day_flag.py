"""add explicit all-day task deadline flag

Revision ID: b318d2f7c641
Revises: f921c410a772
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b318d2f7c641"
down_revision: Union[str, Sequence[str], None] = "f921c410a772"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column(
            "due_date_is_all_day",
            sa.Boolean(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("tasks", "due_date_is_all_day")
