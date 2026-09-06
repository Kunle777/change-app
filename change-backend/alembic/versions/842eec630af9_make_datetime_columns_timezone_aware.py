"""make datetime columns timezone-aware

Revision ID: 842eec630af9
Revises: e67c8763747b
Create Date: 2026-09-06 20:32:41.401196

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '842eec630af9'
down_revision: Union[str, Sequence[str], None] = 'e67c8763747b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE brain_dumps ALTER COLUMN created_at "
        "TYPE timestamptz USING created_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE tasks ALTER COLUMN due_date "
        "TYPE timestamptz USING due_date AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE tasks ALTER COLUMN reminder_time "
        "TYPE timestamptz USING reminder_time AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE tasks ALTER COLUMN created_at "
        "TYPE timestamptz USING created_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE tasks ALTER COLUMN completed_at "
        "TYPE timestamptz USING completed_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE users ALTER COLUMN created_at "
        "TYPE timestamptz USING created_at AT TIME ZONE 'UTC'"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE users ALTER COLUMN created_at "
        "TYPE timestamp USING created_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE tasks ALTER COLUMN completed_at "
        "TYPE timestamp USING completed_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE tasks ALTER COLUMN created_at "
        "TYPE timestamp USING created_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE tasks ALTER COLUMN reminder_time "
        "TYPE timestamp USING reminder_time AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE tasks ALTER COLUMN due_date "
        "TYPE timestamp USING due_date AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE brain_dumps ALTER COLUMN created_at "
        "TYPE timestamp USING created_at AT TIME ZONE 'UTC'"
    )
