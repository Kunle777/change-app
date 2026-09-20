from pydantic import BaseModel, ConfigDict, field_validator
from uuid import UUID
from datetime import datetime
from typing import Optional
from app.tasks.models import PriorityEnum, StatusEnum
from app.tasks.models import RecurrenceEnum


def normalize_task_enum(value, enum_type):
    if isinstance(value, str):
        try:
            return enum_type[value]
        except KeyError:
            pass
    return value

class TaskCreate(BaseModel):
    title: str
    priority: PriorityEnum = PriorityEnum.low
    status: StatusEnum = StatusEnum.pending
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    reminder_time: Optional[datetime] = None
    recurrence: Optional[RecurrenceEnum] = None

    @field_validator('priority', 'status', 'recurrence', mode='before')
    @classmethod
    def accept_enum_names(cls, value, info):
        enum_types = {
            'priority': PriorityEnum,
            'status': StatusEnum,
            'recurrence': RecurrenceEnum,
        }
        return normalize_task_enum(value, enum_types[info.field_name])

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

    @field_validator('priority', 'status', 'recurrence', mode='before')
    @classmethod
    def accept_enum_names(cls, value, info):
        enum_types = {
            'priority': PriorityEnum,
            'status': StatusEnum,
            'recurrence': RecurrenceEnum,
        }
        return normalize_task_enum(value, enum_types[info.field_name])

class TaskReschedule(BaseModel):
    due_date: datetime | None = None
    reminder_time: datetime | None = None


class CalendarDatesResponse(BaseModel):
    dates: list[str]  # ISO date strings ("2026-09-15") that have >=1 task