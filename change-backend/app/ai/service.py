from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.checkins import service as checkin_service
from app.ai.models import AIUsageLog
from app.ai import gemini
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


async def generate_evening_summary(db: AsyncSession, user_id: UUID) -> str:
    # Fetch recent check-ins for the user
    recent_checkins = await checkin_service.get_recent_checkin(db, user_id, days=7)
    if not recent_checkins:
        return "No recent check-ins history yet nothing to summarize."

    # Generate a summary based on the check-ins
    summary_lines = []
    for c in recent_checkins:
        date_str = c.created_at.strftime("%Y-%m-%d")
        summary_lines.append(f"- {date_str} ({c.type.value}): mood {c.mood}/5")
        if c.goal_today:
            summary_lines.append(f"  Goal: {c.goal_today}")
        if c.reflection:
            summary_lines.append(f"  Reflection: {c.reflection}")

    checkin_text = "\n".join(summary_lines)

    prompt = (
    "Here is a user's check-in history from the last 7 days:\n\n"
    f"{checkin_text}\n\n"
    "Write a short, honest, encouraging 3-4 sentence summary noticing any "
    "patterns in mood or recurring themes. Do not invent details not present above.")

    return gemini.generate_response(prompt)

