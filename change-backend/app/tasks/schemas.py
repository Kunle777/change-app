from pydantic import BaseModel, ConfigDict, field_validator
from uuid import UUID
from datetime import date, datetime, time
from typing import Optional, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from pydantic import Field
from app.tasks.models import PriorityEnum, StatusEnum
from app.tasks.models import RecurrenceEnum

def normalize_task_enum(value, enum_type):
    if isinstance(value, str):
        try:
            return enum_type[value]
        except KeyError:
            pass
    return value

class TaskRecurrenceCreate(BaseModel):
    frequency: Literal["daily", "weekly", "monthly"]
    interval: int = Field(default=1, ge=1, le=365)
    days_of_week: list[int] = Field(default_factory=list, max_length=7)
    start_date: date
    local_time: time | None = None
    timezone: str = "Africa/Lagos"
    end_date: date | None = None
    occurrence_limit: int | None = Field(default=None, ge=1, le=10000)

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError("timezone must be a valid IANA time zone") from error
        return value

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, value: date | None, info):
        start_date = info.data.get("start_date")
        if value is not None and start_date is not None and value < start_date:
            raise ValueError("end_date must be on or after start_date")
        return value

    @field_validator("days_of_week")
    @classmethod
    def valid_weekdays(cls, value: list[int], info):
        if any(day < 0 or day > 6 for day in value) or len(set(value)) != len(value):
            raise ValueError("days_of_week must contain unique weekday numbers from 0 to 6")
        if value and info.data.get("frequency") != "weekly":
            raise ValueError("days_of_week is only valid for weekly recurrence")
        return sorted(value)


class TaskCreate(BaseModel):
    title: str
    priority: PriorityEnum = PriorityEnum.low
    status: StatusEnum = StatusEnum.pending
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    reminder_time: Optional[datetime] = None
    recurrence: Optional[RecurrenceEnum] = None
    recurrence_rule: TaskRecurrenceCreate | None = None

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
    series_id: UUID | None = None
    occurrence_date: date | None = None
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
    dates: list[str]


class TaskSnooze(BaseModel):
    snoozed_until: datetime | None = None


class SeriesEditRequest(BaseModel):
    scope: Literal["occurrence", "this_and_future", "entire_series"]
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None
    priority: PriorityEnum
