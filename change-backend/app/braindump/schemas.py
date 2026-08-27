from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional
from app.tasks.models import PriorityEnum, StatusEnum

class BrainDumpCreate(BaseModel):
    content: str

class BrainDumpResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    content: str
    is_converted: bool
    created_at: datetime