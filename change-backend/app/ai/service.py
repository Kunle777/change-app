from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.models import AIUsageLog

DAILY_LIMIT_FREE = 20  # arbitrary for now — real tiering logic is Phase 8


async def check_usage(db: AsyncSession, user_id: UUID) -> None:
    today = date.today()
    result = await db.execute(
        select(AIUsageLog).where(
            AIUsageLog.user_id == user_id,
            AIUsageLog.usage_date == today,
        )
    )
    log = result.scalar_one_or_none()
    if log is not None and log.request_count >= DAILY_LIMIT_FREE:
        raise ValueError("Daily AI usage limit reached")


async def increment_usage(db: AsyncSession, user_id: UUID) -> None:
    today = date.today()
    result = await db.execute(
        select(AIUsageLog).where(
            AIUsageLog.user_id == user_id,
            AIUsageLog.usage_date == today,
        )
    )
    log = result.scalar_one_or_none()
    if log is None:
        db.add(AIUsageLog(user_id=user_id, usage_date=today, request_count=1))
    else:
        log.request_count += 1
    await db.commit()