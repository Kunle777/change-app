from fastapi import APIRouter, Depends
from app.users.models import User
from app.users.dependencies import get_current_user

router = APIRouter(
    prefix="/api/auth",
    tags=["auth"],
)

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
