from pydantic import BaseModel, ConfigDict
from datetime import datetime
import uuid


class WinCreate(BaseModel):
    description: str


class WinResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    description: str
    created_at: datetime
