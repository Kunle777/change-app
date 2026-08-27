from pydantic import BaseModel, ConfigDict, field_validator
from uuid import UUID
from datetime import datetime
from typing import Optional
from app.tasks.models import PriorityEnum, StatusEnum
from app.tasks.models import RecurrenceEnum

class TaskCreate(BaseModel):
    title: str
    priority: PriorityEnum = PriorityEnum.low
    status: StatusEnum = StatusEnum.pending
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    reminder_time: Optional[datetime] = None
    recurrence: Optional[RecurrenceEnum] = None

class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    title: str
    priority: str
    status: str
    description: Optional[str]
    due_date: Optional[datetime]
    reminder_time: Optional[datetime]
    recurrence: Optional[str]
    created_at: datetime

    @field_validator('priority', 'status', mode='before')
    @classmethod
    def enum_to_name(cls, v):
        return v.name if hasattr(v, 'name') else str(v)

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    priority: Optional[PriorityEnum] = None
    status: Optional[StatusEnum] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    reminder_time: Optional[datetime] = None
    recurrence: Optional[RecurrenceEnum] = None
