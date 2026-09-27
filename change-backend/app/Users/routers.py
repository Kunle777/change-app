from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.Users.models import User
from app.Users.dependencies import get_current_user
from app.Users.service import (
    update_fcm_token,
    get_or_create_entitlements,
    set_country_code,
    record_daily_activity,
    get_activity_streak,
)
from app.Users.schemas import EntitlementsResponse, CountryUpdate, UserProfileResponse

router = APIRouter(prefix="/api", tags=["auth"])


class FcmTokenUpdate(BaseModel):
    token: str


class ToggleCheckinsRequest(BaseModel):
    enabled: bool


class ActivityRequest(BaseModel):
    timezone: str = "Africa/Lagos"


# All register/login/refresh/forgot-password/reset-password routes have been
# retired — Supabase Auth handles these client-side via the SDK.

# Hidden token route kept as a no-op so OAuth2PasswordBearer tokenUrl resolves
# without 404 in Swagger UI.
@router.post("/auth/token", include_in_schema=False)
async def swagger_token_placeholder():
    return {"detail": "Use Supabase Auth SDK to obtain tokens."}


@router.get("/auth/profile")
async def get_profile(current_user: User = Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "country_code": current_user.country_code,
    }


@router.patch("/auth/fcm-token")
async def patch_fcm_token(
    data: FcmTokenUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    updated_user = await update_fcm_token(db, current_user, data.token)
    return {"id": str(updated_user.id), "fcm_token": updated_user.fcm_token}


@router.post("/users/activity")
async def record_user_activity(
    payload: ActivityRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await record_daily_activity(db, current_user.id, payload.timezone)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.get("/users/activity")
async def get_user_activity(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_activity_streak(db, current_user.id)


@router.patch("/auth/me/checkins-toggle")
async def toggle_checkins(
    payload: ToggleCheckinsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current_user.checkins_enabled = payload.enabled
    await db.commit()
    return {"checkins_enabled": current_user.checkins_enabled}


@router.patch("/users/country", response_model=EntitlementsResponse)
async def update_country(
    payload: CountryUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await set_country_code(db, current_user.id, payload.country_code)


@router.get("/users/entitlements", response_model=EntitlementsResponse)
async def get_entitlements(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_or_create_entitlements(db, current_user.id)
@router.get("/users/me", response_model=UserProfileResponse)
async def get_my_profile(current_user=Depends(get_current_user)):
    return current_user
