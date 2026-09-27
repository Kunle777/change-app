import enum
import uuid
from datetime import date, datetime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import JSON, String, DateTime, Date, Integer, ForeignKey, Table,Enum as SQLEnum, func
from app.database import Base 

# app/users/models.py — additions

class KYCStatus(str, enum.Enum):
    unverified = "unverified"
    pending = "pending"
    verified = "verified"
    failed = "failed"


class UserTier(str, enum.Enum):
    free = "free"
    premium = "premium"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )
    # remove default=uuid.uuid4 — Supabase Auth generates the ID now, not you
    fcm_token: Mapped[str] = mapped_column(nullable=True)
    phone: Mapped[str] = mapped_column(nullable=True)
    dnd_bypass_enabled: Mapped[bool] = mapped_column(server_default="false", default=False, nullable=False)
    checkins_enabled: Mapped[bool] = mapped_column(server_default="true", default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    #SQLEnum(UserTier, name="user_tier")Tells the database: "Create a custom rule in PostgreSQL named user_tier. If anyone tries to insert a value that isn't 'free' or 'premium', block it and throw an error
    tier: Mapped[UserTier] = mapped_column(SQLEnum(UserTier, name="user_tier"), server_default=UserTier.free.value, default=UserTier.free, nullable=False)
    # remove email and password_hash entirely — Supabase Auth owns these now


    paystack_customer_code: Mapped[str | None] = mapped_column(String, nullable=True)
    dva_account_number: Mapped[str | None] = mapped_column(String, nullable=True)
    dva_bank_name: Mapped[str | None] = mapped_column(String, nullable=True)
    dva_account_name: Mapped[str | None] = mapped_column(String, nullable=True)
    paystack_recipient_code: Mapped[str | None] = mapped_column(String, nullable=True)
    payout_bank_code: Mapped[str | None] = mapped_column(String, nullable=True)
    payout_account_number: Mapped[str | None] = mapped_column(String, nullable=True)
    payout_account_name: Mapped[str | None] = mapped_column(String, nullable=True)  # from Paystack's own verification, not user-typed
    
    kyc_status: Mapped[KYCStatus] = mapped_column(
        SQLEnum(KYCStatus, name="kyc_status"), nullable=False, server_default=KYCStatus.unverified.value
    )
    kyc_verified_name: Mapped[str | None] = mapped_column(String, nullable=True)  # set ONLY by the webhook, never directly

    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String, nullable=True)
    current_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    longest_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_active_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_active_timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
