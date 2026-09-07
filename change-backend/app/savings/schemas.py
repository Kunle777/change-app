# app/savings/schemas.py
from pydantic import BaseModel, Field
from datetime import datetime


class VaultCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    target_amount: float = Field(gt=0)  # required, immutable — per the decision we locked in
    lock_until: datetime


class VaultResponse(BaseModel):
    id: str
    name: str
    target_amount: float
    current_amount: float
    lock_until: datetime
    status: str
    milestone_tier: str

    class Config:
        from_attributes = True