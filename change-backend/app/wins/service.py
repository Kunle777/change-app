import uuid
from datetime import date, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.wins.models import Win
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
    result = await db.execute(
        select(Win.created_at).where(Win.user_id == user_id)
    )
    win_dates = {row[0].date() for row in result.all()}

    if not win_dates:
        return 0

    streak = 0
    cursor = date.today()

    if cursor not in win_dates:
        cursor -= timedelta(days=1)

    while cursor in win_dates:
        streak += 1
        cursor -= timedelta(days=1)

    return streak
