import enum
import uuid
import datetime
from typing import Optional

from sqlalchemy import Enum as SQLEnum, ForeignKey, Text, DateTime, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base
from app.users.models import User

class CheckInType(str, enum.Enum):
    morning = "morning"
    evening = "evening"

class CheckIn(Base):
    __tablename__ = "checkins"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type: Mapped[CheckInType] = mapped_column(SQLEnum(CheckInType, name="checkin_type"), nullable=False)
    mood: Mapped[Optional[int]] = mapped_column(nullable=True)
    goal_today: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reflection: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), nullable=False)