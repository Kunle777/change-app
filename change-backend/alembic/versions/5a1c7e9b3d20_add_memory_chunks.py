"""add memory_chunks for vector retrieval

Revision ID: 5a1c7e9b3d20
Revises: a2c4e6f8b1d3
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector


revision = "5a1c7e9b3d20"
down_revision = "a2c4e6f8b1d3"
branch_labels = None
depends_on = None

EMBEDDING_DIM = 768


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions")

    op.create_table(
        "memory_chunks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_type", sa.String(30), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=False),
        sa.Column("embedding_model", sa.String(60), nullable=False),
        sa.Column("embedding_dim", sa.Integer(), nullable=False),
        sa.Column("source_created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "source_type",
            "source_id",
            "chunk_index",
            name="uq_memory_chunks_source",
        ),
    )
    op.create_index(
        "ix_memory_chunks_user_source",
        "memory_chunks",
        ["user_id", "source_type"],
    )
    op.create_index(
        "ix_memory_chunks_user_created",
        "memory_chunks",
        ["user_id", "source_created_at"],
    )
    op.execute("ALTER TABLE memory_chunks ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_index("ix_memory_chunks_user_created", table_name="memory_chunks")
    op.drop_index("ix_memory_chunks_user_source", table_name="memory_chunks")
    op.drop_table("memory_chunks")
