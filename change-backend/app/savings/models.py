import uuid
import enum
from datetime import datetime
from sqlalchemy import String, Numeric, DateTime, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class VaultStatus(str, enum.Enum):
    active = "active"
    locked_complete = "locked_complete"   # reached lock_until, funds available
    broken = "broken"                     # user broke it early (3.5% fee taken)
    withdrawn = "withdrawn"                # fully paid out


class PendingDepositStatus(str, enum.Enum):
    pending = "pending"
    matched = "matched"
    expired = "expired"


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