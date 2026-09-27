import uuid
import enum
from datetime import date, datetime, time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Date, DateTime, Time, func, ForeignKey, Enum, String, Boolean, Index, text, Integer
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from app.database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.Users.models import User

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


class TaskSeries(Base):
    __tablename__ = "task_series"
    __table_args__ = (Index("ix_task_series_user_active", "user_id", "is_active"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    frequency: Mapped[str] = mapped_column(String(20), nullable=False)
    interval: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    days_of_week: Mapped[list[int]] = mapped_column(
        ARRAY(Integer), nullable=False, default=list, server_default=text("'{}'::integer[]")
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    local_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Africa/Lagos")
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    occurrence_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    generated_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class TaskEventType(str, enum.Enum):
    CREATED = "created"
    REMINDER_SCHEDULED = "reminder_scheduled"
    REMINDER_OPENED = "reminder_opened"
    COMPLETED = "completed"
    NOT_NOW = "not_now"
    RESCHEDULED = "rescheduled"
    CANCELLED = "cancelled"
    OVERDUE = "overdue"
    DEADLINE_CHANGED = "deadline_changed"


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        Index(
            "uq_tasks_series_occurrence_date",
            "series_id",
            "occurrence_date",
            unique=True,
            postgresql_where=text("series_id IS NOT NULL AND occurrence_date IS NOT NULL"),
        ),
    )

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
    priority_reminder: Mapped[bool] = mapped_column(Boolean, server_default="false", default=False, nullable=False)
    recurrence_processed: Mapped[bool] = mapped_column(server_default="false", default=False, nullable=False)
    series_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("task_series.id", ondelete="SET NULL"), nullable=True, index=True
    )
    occurrence_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_brain_dump_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brain_dumps.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    user: Mapped[User] = relationship("User", foreign_keys=[user_id], primaryjoin="Task.user_id == User.id")
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, server_default="false")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TaskEvent(Base):
    __tablename__ = "task_events"
    __table_args__ = (
        Index(
            "uq_task_events_overdue_deadline",
            "task_id",
            text("(event_metadata->>'due_date')"),
            unique=True,
            postgresql_where=text("event_type = 'overdue' AND task_id IS NOT NULL"),
        ),
        Index(
            "uq_task_events_reminder_open_notification",
            "task_id",
            text("(event_metadata->>'notification_id')"),
            unique=True,
            postgresql_where=text("event_type = 'reminder_opened' AND task_id IS NOT NULL"),
        ),
        Index(
            "uq_task_events_reminder_scheduled_notification",
            "task_id",
            text("(event_metadata->>'notification_id')"),
            unique=True,
            postgresql_where=text("event_type = 'reminder_scheduled' AND task_id IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    event_metadata: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class TaskEventOutbox(Base):
    __tablename__ = "task_event_outbox"
    __table_args__ = (
        Index(
            "uq_task_event_outbox_overdue_deadline",
            "task_id",
            text("(event_metadata->>'due_date')"),
            unique=True,
            postgresql_where=text("event_type = 'overdue' AND task_id IS NOT NULL"),
        ),
        Index(
            "uq_task_event_outbox_reminder_open_notification",
            "task_id",
            text("(event_metadata->>'notification_id')"),
            unique=True,
            postgresql_where=text("event_type = 'reminder_opened' AND task_id IS NOT NULL"),
        ),
        Index(
            "uq_task_event_outbox_reminder_scheduled_notification",
            "task_id",
            text("(event_metadata->>'notification_id')"),
            unique=True,
            postgresql_where=text("event_type = 'reminder_scheduled' AND task_id IS NOT NULL"),
        ),
        Index("ix_task_event_outbox_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_metadata: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    attempts: Mapped[int] = mapped_column(nullable=False, server_default="0")
    last_error: Mapped[str | None] = mapped_column(String(100), nullable=True)
