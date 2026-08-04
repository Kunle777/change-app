from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BrainDumpCreate(BaseModel):
    content: str


class BrainDumpResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    content: str
    is_converted: bool
    created_at: datetime
