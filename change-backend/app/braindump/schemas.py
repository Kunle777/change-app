from datetime import date, datetime
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SuggestedRecurrenceRule(BaseModel):
    frequency: Literal["daily", "weekly", "monthly"]
    interval: int = Field(default=1, ge=1, le=365)
    days_of_week: list[int] = Field(default_factory=list, max_length=7)
    timezone: str = "Africa/Lagos"
    start_date: date | None = None
    end_date: date | None = None
    occurrence_limit: int | None = Field(default=None, ge=1, le=10000)

    @field_validator("days_of_week")
    @classmethod
    def validate_days(cls, value: list[int], info):
        if any(day < 0 or day > 6 for day in value) or len(set(value)) != len(value):
            raise ValueError("days_of_week must contain unique weekday numbers from 0 to 6")
        if value and info.data.get("frequency") != "weekly":
            raise ValueError("days_of_week is only valid for weekly recurrence")
        return sorted(value)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError("timezone must be a valid IANA time zone") from error
        return value


class BrainDumpCreate(BaseModel):
    content: str
    source: Literal["text", "voice"] = "text"


class BrainDumpResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    content: str
    source: Literal["text", "voice"]
    is_converted: bool
    created_task_id: UUID | None = None
    created_at: datetime
    possible_task: bool = False


class ParsedTaskSuggestion(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    priority: Literal["low", "medium", "high"] = "medium"
    recurrence_rule: SuggestedRecurrenceRule | None = None

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Task title cannot be blank")
        return value


class ParseDumpResponse(BaseModel):
    suggestions: list[ParsedTaskSuggestion]


class ConvertRequest(BaseModel):
    suggestions: list[ParsedTaskSuggestion] = Field(max_length=30)
