from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr

from app.database import get_db
from app.users.models import User
from app.users.dependencies import get_current_user
from app.users.security import create_access_token, hash_password, verify_password
from app.users.security import limiter
from fastapi.security import OAuth2PasswordRequestForm


router = APIRouter(
    prefix="/api/auth",
    tags=["auth"],
)

# 1. This hidden route exists PURELY to feed the green Authorize button
@router.post("/token", include_in_schema=False)
async def swagger_login(
    data: OAuth2PasswordRequestForm = Depends(), 
    db: AsyncSession = Depends(get_db)
):
    # This just calls your exact same login logic using data.username (email)
    existing = await db.execute(select(User).where(User.email == data.username))
    user = existing.scalar_one_or_none()
    
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(str(user.id))
    return {"access_token": token, "token_type": "bearer"}


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

    
@router.post("/register",response_model=TokenResponse)
async def register(request: Request, data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        email=data.email,
        password_hash=hash_password(data.password)
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    token = create_access_token(str(new_user.id))
    return TokenResponse(access_token=token)
    
@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")  # Limit to 5 requests per minute
async def login(request: Request, data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token)

@router.get("/profile")
async def get_profile(current_user: User = Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "email": current_user.email,
    }

