"""add_recurrence_processed_to_tasks

Revision ID: e67c8763747b
Revises: d022953d588e
Create Date: 2026-08-16 22:28:40.347734

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e67c8763747b'
down_revision: Union[str, Sequence[str], None] = 'd022953d588e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tasks', sa.Column('recurrence_processed', sa.Boolean(), server_default='false', nullable=False))


def downgrade() -> None:
    op.drop_column('tasks', 'recurrence_processed')
