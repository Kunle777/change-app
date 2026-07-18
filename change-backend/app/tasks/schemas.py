from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional
from app.tasks.models import PriorityEnum, StatusEnum

class TaskCreate(BaseModel):
    title: str
    priority: PriorityEnum = PriorityEnum.low
    status: StatusEnum = StatusEnum.pending
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    reminder_time: Optional[datetime] = None
    recurrence: Optional[str] = None

class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    title: str
    priority: PriorityEnum
    status: StatusEnum
    description: Optional[str]
    due_date: Optional[datetime]
    reminder_time: Optional[datetime]
    recurrence: Optional[str]
    created_at: datetime
