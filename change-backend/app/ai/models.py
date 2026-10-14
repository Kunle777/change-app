import uuid 
import enum
from datetime import datetime, timedelta, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Date, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class AIUsageLog(Base):
    __tablename__ = "ai_usage_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    usage_date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    request_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    __table_args__ = (UniqueConstraint("user_id", "usage_date", name="uq_user_usage_date"),)


class Conversation(Base):
    __tablename__ = "ai_conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"), index=True)


class PendingActionStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    EXPIRED = "expired"
    STALE = "stale"


class PendingAction(Base):
    __tablename__ = "pending_actions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ai_conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tool_name: Mapped[str] = mapped_column(String(50), nullable=False)
    summary: Mapped[str] = mapped_column(String(300), nullable=False)
    arguments: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=PendingActionStatus.PENDING.value,
        server_default=PendingActionStatus.PENDING.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc) + timedelta(minutes=10),
        server_default=text("now() + interval '10 minutes'"),
    )


class AIInteraction(Base):
    __tablename__ = "ai_interactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ai_conversations.id", ondelete="SET NULL"), nullable=True, index=True)
    pending_action_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("pending_actions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    intent: Mapped[str | None] = mapped_column(String, nullable=True)
    question: Mapped[str] = mapped_column(String, nullable=False)
    response: Mapped[str] = mapped_column(String, nullable=False)
    context_used: Mapped[str | None] = mapped_column(String, nullable=True)
    context_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tool_used: Mapped[bool] = mapped_column(Boolean, server_default="false", default=False)
    tool_name: Mapped[str | None] = mapped_column(String, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    was_helpful: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    context_richness: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String, server_default="success", default="success")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
