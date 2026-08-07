import uuid
from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime
from typing import Optional
from app.checkins.models import CheckInType

class CheckInCreate(BaseModel):
    mood: Optional[int] = Field(default=None, ge=1, le=5, description="Mood score mapped to 5 emojis: 1 (Very Bad) to 5 (Very Good)")

class MorningCheckInCreate(CheckInCreate):
    goal_today: Optional[str] = None

class EveningCheckInCreate(CheckInCreate):
    reflection: Optional[str] = None

class CheckInResponse(BaseModel):
        model_config = ConfigDict(from_attributes=True)
        id: uuid.UUID
        user_id: uuid.UUID
        type: CheckInType
        mood: Optional[int]
        goal_today: Optional[str]
        reflection: Optional[str]
        ai_summary: Optional[str]
        created_at: datetime