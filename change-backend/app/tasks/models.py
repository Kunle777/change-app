import uuid
import enum
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import DateTime, func, ForeignKey, Enum, String, Boolean
from app.database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.users.models import User

class PriorityEnum(enum.Enum):
    low = 1
    medium = 2
    high = 3

class StatusEnum(enum.Enum):
    pending = 1
    in_progress = 2
    completed = 3
    cancelled = 4

class RecurrenceEnum(enum.Enum):
    none = 0
    daily = 1
    weekly = 2
    monthly = 3


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(nullable=False)
    priority: Mapped[PriorityEnum] = mapped_column(Enum(PriorityEnum), nullable=False, server_default="low")
    status: Mapped[StatusEnum] = mapped_column(Enum(StatusEnum), nullable=False, server_default="pending")
    description: Mapped[str] = mapped_column(nullable=True)
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    reminder_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    recurrence: Mapped[str] = mapped_column(String(), nullable=True, default=None)
    is_reminder_sent: Mapped[bool] = mapped_column(server_default="false", default=False, nullable=False)
    recurrence_processed: Mapped[bool] = mapped_column(server_default="false", default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    user: Mapped[User] = relationship("User", foreign_keys=[user_id], primaryjoin="Task.user_id == User.id")
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, server_default="false")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)