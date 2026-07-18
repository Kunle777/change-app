import uuid
import enum
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import func, ForeignKey, Enum
from app.database import Base
from sqlalchemy.orm import Mapped, mapped_column

class PriorityEnum(enum.Enum):
    low = 1
    medium = 2
    high = 3

class StatusEnum(enum.Enum):
    pending = 1
    in_progress = 2
    completed = 3
    cancelled = 4

class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(nullable=False)
    priority: Mapped[PriorityEnum] = mapped_column(Enum(PriorityEnum), nullable=False, server_default="low")
    status: Mapped[StatusEnum] = mapped_column(Enum(StatusEnum), nullable=False, server_default="pending")
    description: Mapped[str] = mapped_column(nullable=True)
    due_date: Mapped[datetime] = mapped_column(nullable=True)
    reminder_time: Mapped[datetime] = mapped_column(nullable=True)
    recurrence: Mapped[str] = mapped_column(nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
