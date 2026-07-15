from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
import os
from jose import JWTError, jwt
from datetime import datetime, timedelta

from app.database import get_db
from app.users.models import User
from app.users.dependencies import get_current_user
from app.users.security import create_access_token, hash_password, verify_password,create_refresh_token, decode_refresh_token
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
    refresh_token: str
    token_type: str = "bearer"

class ForgotPassword(BaseModel):
    email: EmailStr
    
class ResetPasswordRequest(BaseModel):
    token:str
    new_password: str

class RefreshRequest(BaseModel):
    refresh_token: str

    
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
    access_token = create_access_token(str(new_user.id))
    refresh_token = create_refresh_token(str(new_user.id))
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)
    
@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")  # Limit to 5 requests per minute
async def login(request: Request, data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    token = create_access_token(str(user.id))
    access_token = create_access_token(str(user.id))
    refresh_token = decode_refresh_token(str(user.id))
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)
                                        

@router.get("/profile")
async def get_profile(current_user: User = Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "email": current_user.email,
    }



@router.post("/forgot-password")
async def forgot_password(data: ForgotPassword, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if user is None:
        return{
        "message": "If this email exists, a reset link has been sent."
    }
    reset_token_expiry = datetime.utcnow() + timedelta(minutes=15)
    reset_payload = {
        "sub": str(user.id),
        "purpose": "password_reset",
        "exp": reset_token_expiry
    }

    reset_token = jwt.encode(reset_payload, os.getenv("JWT_SECRET_KEY"), algorithm=os.getenv("JWT_ALGORITHM"))

    return {
        "message" : "if this email exist a reset link has been generated",
        "def_reset_token": reset_token
    }

@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = jwt.decode(data.token, os.getenv("JWT_SECRET_KEY"), algorithms=[os.getenv("JWT_ALGORITHM")])
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
        
    if payload.get("purpose")!= "password_reset":
        raise HTTPException(status_code=400, detail="Invalid token type")
    
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code= 404, detail="User not found")
    
    user.password_hash = hash_password(data.new_password)
    await db.commit()

    return {"message": "Password has been reset successfully"}

@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = jwt.decode(data.token, os.getenv("JWT_SECRET_KEY"), algorithms=[os.getenv("JWT_ALGORITHM")])
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
        
    if payload.get("purpose") != "password_reset":
        raise HTTPException(status_code=400, detail="Invalid token type")
    
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 2. Fixed variable name to use new_password with underscore
    user.password_hash = hash_password(data.new_password)
    await db.commit()

    return {"message": "Password has been reset successfully"}