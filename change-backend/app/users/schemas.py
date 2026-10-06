from pydantic import BaseModel, ConfigDict


class CountryUpdate(BaseModel):
    country_code: str  # ISO 3166-1 alpha-2, e.g. "NG", "US"


class EntitlementsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    savings_enabled: bool
    ai_enabled: bool
    brain_dump_enabled: bool
    premium: bool

class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    first_name: str | None