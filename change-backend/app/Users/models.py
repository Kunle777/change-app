import enum
import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Column, ForeignKey, Table,Enum as SQLEnum, func
from app.database import Base 



class UserTier(enum.Enum):
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
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    #SQLEnum(UserTier, name="user_tier")Tells the database: "Create a custom rule in PostgreSQL named user_tier. If anyone tries to insert a value that isn't 'free' or 'premium', block it and throw an error
    tier: Mapped[UserTier] = mapped_column(SQLEnum(UserTier, name="user_tier"), server_default=UserTier.free.value, default=UserTier.free, nullable=False)
    checkins_enabled: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="true")