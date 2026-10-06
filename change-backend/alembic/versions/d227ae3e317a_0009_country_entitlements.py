"""0009_country_entitlements

Revision ID: d227ae3e317a
Revises: 31f531df0730
Create Date: 2026-09-12
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

revision = "d227ae3e317a"
down_revision = "31f531df0730"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column("country_code", sa.String(2), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("first_name", sa.String, nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("avatar_url", sa.String, nullable=True),
    )

    op.create_table(
        "feature_entitlements",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column(
            "savings_enabled",
            sa.Boolean,
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "ai_enabled",
            sa.Boolean,
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "brain_dump_enabled",
            sa.Boolean,
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "premium",
            sa.Boolean,
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )


def downgrade():
    op.drop_table("feature_entitlements")
    op.drop_column("users", "avatar_url")
    op.drop_column("users", "first_name")
    op.drop_column("users", "country_code")