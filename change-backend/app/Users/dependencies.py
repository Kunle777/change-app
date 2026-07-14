from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.users.security import decode_access_token
from app.users.models import User
from sqlalchemy import select

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")



async def get_current_user(
        token:str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db)
) -> User:
    user_id = decode_access_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user