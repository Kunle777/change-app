"""add source, created_task_id to brain_dumps

Revision ID: 0014_brain_dump_fields
Revises: 5ef74f73add1
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0014_brain_dump_fields"
down_revision = "5ef74f73add1"


def upgrade():
    op.add_column("brain_dumps", sa.Column("source", sa.String, nullable=False, server_default="text"))
    op.add_column(
        "brain_dumps",
        sa.Column(
            "created_task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade():
    op.drop_column("brain_dumps", "created_task_id")
    op.drop_column("brain_dumps", "source")
