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


class BankAccountSetup(BaseModel):
    first_name: str
    last_name: str
    bvn: str = Field(min_length=11, max_length=11)
    bank_code: str
    account_number: str = Field(min_length=10, max_length=10)


class BankAccountChangeRequest(BaseModel):
    withdrawal_pin: str
    new_bvn: str
    new_bank_code: str
    new_account_number: str
    first_name: str
    last_name: str