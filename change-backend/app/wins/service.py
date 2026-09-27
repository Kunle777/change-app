import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.wins.models import Win
from app.users.models import User
from app.wins.schemas import WinCreate


async def create_win(db: AsyncSession, user_id: uuid.UUID, data: WinCreate) -> Win:
    win = Win(user_id=user_id, description=data.description)
    db.add(win)
    await db.commit()
    await db.refresh(win)
    return win


async def get_wins(db: AsyncSession, user_id: uuid.UUID, limit: int = 50) -> list[Win]:
    result = await db.execute(
        select(Win)
        .where(Win.user_id == user_id)
        .order_by(Win.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_current_streak(db: AsyncSession, user_id: uuid.UUID) -> int:
    result = await db.execute(select(User.current_streak).where(User.id == user_id))
    return result.scalar_one_or_none() or 0
