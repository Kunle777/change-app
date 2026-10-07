"""remove Savings and Paystack application schema

Revision ID: c814f9a1d70e
Revises: 8b36e0c17a29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c814f9a1d70e"
down_revision: Union[str, Sequence[str], None] = "8b36e0c17a29"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Child tables must be dropped before the vault table they reference.
    op.drop_table("pending_deposits")
    op.drop_table("savings_transactions")
    op.drop_table("platform_revenue")
    op.drop_table("savings_vaults")

    op.drop_column("feature_entitlements", "savings_enabled")

    for column in (
        "paystack_customer_code", "dva_account_number", "dva_bank_name",
        "dva_account_name", "paystack_recipient_code", "payout_bank_code",
        "payout_account_number", "payout_account_name", "kyc_verified_name",
        "kyc_status",
    ):
        op.drop_column("users", column)

    for enum_name in (
        "pending_deposit_status", "transaction_type", "transaction_status",
        "vault_status", "kyc_status",
    ):
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")


def downgrade() -> None:
    # Downgrade restores schema only; data dropped by upgrade cannot be recovered.
    kyc_status = postgresql.ENUM(
        "unverified", "pending", "verified", "failed", name="kyc_status"
    )
    pending_status = postgresql.ENUM(
        "pending", "matched", "expired", name="pending_deposit_status"
    )
    transaction_type = postgresql.ENUM("deposit", "withdrawal", name="transaction_type")
    transaction_status = postgresql.ENUM(
        "pending", "success", "failed", name="transaction_status"
    )
    vault_status = postgresql.ENUM(
        "active", "awaiting_bank_details", "payout_initiated",
        "withdrawn", "payout_failed", "broken", name="vault_status"
    )
    for enum_type in (
        kyc_status, pending_status, transaction_type, transaction_status, vault_status
    ):
        enum_type.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "feature_entitlements",
        sa.Column("savings_enabled", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column("users", sa.Column("kyc_status", kyc_status, server_default="unverified", nullable=False))
    op.add_column("users", sa.Column("kyc_verified_name", sa.String(), nullable=True))
    for column in (
        "paystack_customer_code", "dva_account_number", "dva_bank_name",
        "dva_account_name", "paystack_recipient_code", "payout_bank_code",
        "payout_account_number", "payout_account_name",
    ):
        op.add_column("users", sa.Column(column, sa.String(), nullable=True))

    op.create_table(
        "savings_vaults",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("target_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("current_amount", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("lock_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", vault_status, server_default="active", nullable=False),
        sa.Column("milestone_tier", sa.String(), nullable=False),
        sa.Column("cooling_off_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("milestones_reached", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_savings_vaults_user_id", "savings_vaults", ["user_id"])

    op.create_table(
        "pending_deposits",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vault_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("expected_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", pending_status, server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["vault_id"], ["savings_vaults.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pending_deposits_vault_id", "pending_deposits", ["vault_id"])
    op.create_index("ix_pending_deposits_user_id", "pending_deposits", ["user_id"])

    op.create_table(
        "savings_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vault_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("type", transaction_type, nullable=False),
        sa.Column("paystack_reference", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("status", transaction_status, server_default="success", nullable=False),
        sa.ForeignKeyConstraint(["vault_id"], ["savings_vaults.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_savings_transactions_paystack_reference", "savings_transactions", ["paystack_reference"], unique=True)
    op.create_index("ix_savings_transactions_user_id", "savings_transactions", ["user_id"])
    op.create_index("ix_savings_transactions_vault_id", "savings_transactions", ["vault_id"])

    op.create_table(
        "platform_revenue",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vault_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("withdrawn", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("withdrawal_reference", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["vault_id"], ["savings_vaults.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
