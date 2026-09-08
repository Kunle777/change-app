"""replace vault status enum with payout lifecycle statuses

Revision ID: 6c2d9e7f4a11
Revises: 0bf1acfafb73
Create Date: 2026-09-08

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "6c2d9e7f4a11"
down_revision: Union[str, Sequence[str], None] = "0bf1acfafb73"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


NEW_STATUSES = (
    "active",
    "awaiting_bank_details",
    "payout_initiated",
    "withdrawn",
    "payout_failed",
    "broken",
)


def upgrade() -> None:
    """Replace the PostgreSQL enum and preserve legacy vault rows."""
    op.execute("ALTER TABLE savings_vaults ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TYPE vault_status RENAME TO vault_status_old")
    op.execute(
        "CREATE TYPE vault_status AS ENUM ("
        + ", ".join(f"'{status}'" for status in NEW_STATUSES)
        + ")"
    )
    op.execute(
        "ALTER TABLE savings_vaults ALTER COLUMN status TYPE vault_status "
        "USING (CASE status::text "
        "WHEN 'locked_complete' THEN 'awaiting_bank_details' "
        "ELSE status::text END)::vault_status"
    )
    op.execute("ALTER TABLE savings_vaults ALTER COLUMN status SET DEFAULT 'active'")
    op.execute("DROP TYPE vault_status_old")


def downgrade() -> None:
    """Restore the original enum, mapping new payout states conservatively."""
    op.execute("ALTER TABLE savings_vaults ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TYPE vault_status RENAME TO vault_status_new")
    op.execute(
        "CREATE TYPE vault_status AS ENUM "
        "('active', 'locked_complete', 'broken', 'withdrawn')"
    )
    op.execute(
        "ALTER TABLE savings_vaults ALTER COLUMN status TYPE vault_status "
        "USING (CASE status::text "
        "WHEN 'awaiting_bank_details' THEN 'locked_complete' "
        "WHEN 'payout_initiated' THEN 'locked_complete' "
        "WHEN 'payout_failed' THEN 'active' "
        "ELSE status::text END)::vault_status"
    )
    op.execute("ALTER TABLE savings_vaults ALTER COLUMN status SET DEFAULT 'active'")
    op.execute("DROP TYPE vault_status_new")
