import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.database import Base


class FeatureEntitlements(Base):
    __tablename__ = "feature_entitlements"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_feature_entitlements_user_id"),
        Index("ix_feature_entitlements_user_id", "user_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    ai_enabled: Mapped[bool] = mapped_column(Boolean, server_default="true")
    brain_dump_enabled: Mapped[bool] = mapped_column(Boolean, server_default="true")
    premium: Mapped[bool] = mapped_column(Boolean, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )