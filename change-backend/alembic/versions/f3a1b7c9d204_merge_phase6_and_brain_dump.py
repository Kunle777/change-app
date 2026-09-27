"""merge task-series and brain-dump migration heads

Revision ID: f3a1b7c9d204
Revises: 0014_brain_dump_fields, c814d62a9f31
"""
from typing import Sequence, Union

revision: str = "f3a1b7c9d204"
down_revision: Union[str, Sequence[str], None] = (
    "0014_brain_dump_fields",
    "c814d62a9f31",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
