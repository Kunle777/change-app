import json
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.checkins import service as checkin_service
from app.ai.models import AIUsageLog
from app.ai import gemini
from app.ai.prompt_builder import build_prompt
from app.ai.context_builder import build_context
from app.ai.schemas import ChatResponse
from app.ai.intent_router import detect_intent
from app.ai.models import AIInteraction
from app.ai.gemini import generate_structured

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



async def check_usage(db: AsyncSession, user_id) -> bool:
    today = date.today()
    result = await db.execute(
        select(AIUsageLog).where(
            AIUsageLog.user_id == user_id, AIUsageLog.usage_date == today
        )
    )
    log = result.scalar_one_or_none()
    DAILY_LIMIT = 30
    return not log or log.request_count < DAILY_LIMIT


async def increment_usage(db: AsyncSession, user_id):
    today = date.today()
    result = await db.execute(
        select(AIUsageLog).where(
            AIUsageLog.user_id == user_id, AIUsageLog.usage_date == today
        )
    )
    log = result.scalar_one_or_none()
    if log:
        log.request_count += 1
    else:
        log = AIUsageLog(user_id=user_id, usage_date=today, request_count=1)
        db.add(log)
    await db.commit()


async def handle_chat(db: AsyncSession, user_id, message: str) -> ChatResponse:
    if len(message) > 2000:
        raise ValueError("Message too long")

    intent = detect_intent(message)
    context = await build_context(db, user_id, intent)
    prompt = build_prompt(intent, context, message)

    raw = await generate_structured(prompt)  # existing Gemini JSON-mode wrapper

    try:
        parsed = json.loads(raw) if isinstance(raw, str) else raw
        response = ChatResponse(
            intent=parsed.get("intent", intent),
            message=parsed.get("message", "Sorry, I couldn't process that."),
            suggested_actions=parsed.get("suggested_actions", []),
        )
    except Exception:
        response = ChatResponse(
            intent="general_coaching",
            message="I had trouble understanding that — could you rephrase?",
            suggested_actions=[],
        )

    db.add(
        AIInteraction(
            user_id=user_id,
            intent=response.intent,
            question=message,
            response=response.message,
            context_used=context,
            context_size=len(context),
            status="success",
        )
    )
    await db.commit()

    return response