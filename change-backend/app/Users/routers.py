from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.users.models import User
from app.users.dependencies import get_current_user
from app.users.service import update_fcm_token

router = APIRouter(
    prefix="/api/auth",
    tags=["auth"],
)


class FcmTokenUpdate(BaseModel):
    token: str


class ToggleCheckinsRequest(BaseModel):
    enabled: bool


# All register/login/refresh/forgot-password/reset-password routes have been
# retired — Supabase Auth handles these client-side via the SDK.

# Hidden token route kept as a no-op so OAuth2PasswordBearer tokenUrl resolves
# without 404 in Swagger UI.
@router.post("/token", include_in_schema=False)
async def swagger_token_placeholder():
    return {"detail": "Use Supabase Auth SDK to obtain tokens."}


@router.get("/profile")
async def get_profile(current_user: User = Depends(get_current_user)):
    return {"id": str(current_user.id)}


@router.patch("/fcm-token")
async def patch_fcm_token(
    data: FcmTokenUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    updated_user = await update_fcm_token(db, current_user, data.token)
    return {"id": str(updated_user.id), "fcm_token": updated_user.fcm_token}


@router.patch("/me/checkins-toggle")
async def toggle_checkins(
    payload: ToggleCheckinsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current_user.checkins_enabled = payload.enabled
    await db.commit()
    return {"checkins_enabled": current_user.checkins_enabled}

