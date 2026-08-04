from sqlalchemy.ext.asyncio import AsyncSession
from app.users.models import User


async def update_fcm_token(db: AsyncSession, user: User, token: str) -> User:
    user.fcm_token = token
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
