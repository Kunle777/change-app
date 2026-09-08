import uuid
import enum
from datetime import datetime
from sqlalchemy import String, Numeric, DateTime, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class VaultStatus(str, enum.Enum):
    active = "active"
    awaiting_bank_details = "awaiting_bank_details"
    payout_initiated = "payout_initiated"
    withdrawn = "withdrawn"
    payout_failed = "payout_failed"
    broken = "broken"


class PendingDepositStatus(str, enum.Enum):
    pending = "pending"
    matched = "matched"
    expired = "expired"


class TransactionType(str, enum.Enum):
    deposit = "deposit"
    withdrawal = "withdrawal"
    # break_vault / emergency_withdrawal fee variants added in Day 8



class TransactionStatus(str, enum.Enum):
    pending = "pending"
    success = "success"
    failed = "failed"


class SavingsVault(Base):
    __tablename__ = "savings_vaults"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)

    name: Mapped[str] = mapped_column(String, nullable=False)
    target_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    current_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, server_default="0")

    lock_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[VaultStatus] = mapped_column(
        SQLEnum(VaultStatus, name="vault_status"),
        nullable=False,
        server_default=VaultStatus.active.value,
    )

    # milestone_tier stored at creation — decided in memory, never recomputed later
    # "short" = ≤3 months
    # "long"  = >3 months
    milestone_tier: Mapped[str] = mapped_column(String, nullable=False)

    cooling_off_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    milestones_reached: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    user = relationship("User")


class PendingDeposit(Base):
    __tablename__ = "pending_deposits"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    vault_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("savings_vaults.id"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    expected_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[PendingDepositStatus] = mapped_column(
        SQLEnum(PendingDepositStatus, name="pending_deposit_status"),
        nullable=False,
        server_default=PendingDepositStatus.pending.value,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    vault = relationship("SavingsVault")


class SavingsTransaction(Base):
    __tablename__ = "savings_transactions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    vault_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("savings_vaults.id"), nullable=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    type: Mapped[TransactionType] = mapped_column(
        SQLEnum(TransactionType, name="transaction_type"), nullable=False
    )

    # This is the idempotency anchor — a unique constraint means the DB
    # itself refuses a second row with the same reference, so double-crediting
    # is impossible even if the webhook handler's own check has a bug.
    paystack_reference: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    status: Mapped[TransactionStatus] = mapped_column(
    SQLEnum(TransactionStatus, name="transaction_status"),
    nullable=False,
    server_default=TransactionStatus.success.value,  # deposits are already-confirmed by the time we insert them
)


    vault = relationship("SavingsVault")