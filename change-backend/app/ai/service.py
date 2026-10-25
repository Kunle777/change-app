import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.checkins import service as checkin_service
from app.ai.models import AIUsageLog
from app.ai import gemini
from app.ai.prompt_builder import build_system_prompt_for_user
from app.ai.freshness_service import resolve_user_timezone
from app.ai.context_service import assemble_coaching_context
from app.ai.schemas import ChatResponse, ConversationDetail, ConversationSummary, ConversationTurn

from app.ai.models import AIInteraction, Conversation
from app.ai import action_service
from app.memory.sources import CONVERSATION_SOURCE, is_indexable_user_message
from app.memory.tasks import enqueue_memory_source_index
from app.users.models import User

logger = logging.getLogger(__name__)

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

    system_prompt, _ = await build_system_prompt_for_user(
        db,
        user_id,
        "daily_review",
        checkin_text,
        additional_instructions=(
            "Write a short, honest, encouraging 3-4 sentence summary noticing any "
            "patterns in mood or recurring themes. Do not invent details not present "
            "in the supplied check-in history."
        ),
    )
    return await asyncio.to_thread(gemini.generate_response, system_prompt)



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


async def list_conversations(db: AsyncSession, user_id: UUID) -> list[ConversationSummary]:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
        .limit(50)
    )
    return [
        ConversationSummary(id=item.id, title=item.title, updated_at=item.updated_at)
        for item in result.scalars().all()
    ]


async def get_conversation(
    db: AsyncSession, user_id: UUID, conversation_id: UUID
) -> ConversationDetail | None:
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        return None

    interaction_result = await db.execute(
        select(AIInteraction)
        .where(
            AIInteraction.conversation_id == conversation_id,
            AIInteraction.user_id == user_id,
        )
        .order_by(AIInteraction.created_at.desc())
        .limit(100)
    )
    interactions = list(interaction_result.scalars().all())
    interactions.reverse()
    messages = [
        ConversationTurn(
            id=item.id,
            question=item.question,
            response=item.response,
            intent=item.intent,
            created_at=item.created_at,
            pending_action_id=item.pending_action_id,
        )
        for item in interactions
    ]
    return ConversationDetail(
        id=conversation.id,
        title=conversation.title,
        updated_at=conversation.updated_at,
        messages=messages,
    )


async def continue_conversation(
    db: AsyncSession, user_id: UUID, conversation_id: UUID
) -> Conversation | None:
    """Continue an explicitly selected conversation without applying age boundaries."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def get_or_create_active_conversation(
    db: AsyncSession,
    user_id: UUID,
    first_message: str,
    timezone_name: str | None = None,
) -> Conversation:
    now = datetime.now(timezone.utc)
    user_timezone = await resolve_user_timezone(db, user_id, timezone_name)
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
        .limit(1)
    )
    conversation = result.scalar_one_or_none()
    if (
        conversation is not None
        and conversation.updated_at.astimezone(user_timezone).date()
        == now.astimezone(user_timezone).date()
        and conversation.updated_at >= now - timedelta(hours=3)
    ):
        return conversation

    title = " ".join(first_message.split())[:120] or "New conversation"
    conversation = Conversation(user_id=user_id, title=title, updated_at=now)
    db.add(conversation)
    await db.flush()
    return conversation


async def handle_chat(
    db: AsyncSession,
    user: User,
    message: str,
    conversation_id: UUID | None = None,
    timezone_name: str | None = None,
) -> ChatResponse:
    user_id = user.id
    if len(message) > 2000:
        raise ValueError("Message too long")

    if conversation_id is None:
        conversation = await get_or_create_active_conversation(
            db, user_id, message, timezone_name
        )
    else:
        conversation = await continue_conversation(db, user_id, conversation_id)
        if conversation is None:
            raise LookupError("Conversation not found")

    coaching = await assemble_coaching_context(
        db,
        user_id=user_id,
        message=message,
        conversation_id=conversation.id,
        timezone_name=timezone_name,
    )
    intent = coaching.intent
    status = "success"
    pending_action_id = None
    pending_action_summary = None
    tool_used = False
    tool_name_used = None
    try:
        generated = await asyncio.to_thread(
            gemini.generate_chat_response_with_tools,
            coaching.system_prompt,
            coaching.history,
            message,
            allow_tools=coaching.allow_tools,
        )
        tool_call = generated.get("tool_call")
        if tool_call is None:
            final_message = generated.get("text") or "I couldn't finish that response."
        else:
            tool_name = tool_call.get("name")
            tool_used = True
            tool_name_used = tool_name
            arguments = tool_call.get("args") or {}
            outcome = await action_service.handle_tool_call(
                db,
                user=user,
                conversation_id=conversation.id,
                tool_name=tool_name,
                arguments=arguments,
                force_confirmation=coaching.require_confirmation,
            )
            if outcome.get("status") == "awaiting_confirmation":
                pending_action_id = UUID(outcome["pending_action_id"])
                pending_action_summary = outcome["summary"]
                try:
                    await asyncio.to_thread(
                        gemini.send_tool_result, generated["chat"], tool_name, outcome
                    )
                except Exception:
                    pass
                final_message = (
                    f"I haven't changed anything yet. {pending_action_summary} "
                    "Please confirm or reject it below."
                )
            else:
                try:
                    final_message = await asyncio.to_thread(
                        gemini.send_tool_result,
                        generated["chat"],
                        tool_name,
                        outcome,
                    )
                except Exception:
                    if outcome.get("status") == "created":
                        final_message = f"Created task: {outcome.get('title', 'your task')}."
                    elif outcome.get("status") == "error":
                        final_message = (
                            "I couldn't make that change: "
                            f"{outcome.get('reason', 'the request was invalid')}."
                        )
                    else:
                        final_message = "The task action completed."
    except Exception:
        logger.exception("Gemini chat generation failed")
        status = "error"
        final_message = "I'm having trouble responding right now. Please try again in a moment."

    conversation.updated_at = datetime.now(timezone.utc)
    interaction = AIInteraction(
        user_id=user_id,
        conversation_id=conversation.id,
        pending_action_id=pending_action_id,
        intent=intent,
        question=message,
        response=final_message,
        context_used=coaching.context_used,
        context_size=len(coaching.context_used),
        context_richness=coaching.freshness.tier.value,
        tool_used=tool_used,
        tool_name=tool_name_used,
        status=status,
    )
    db.add(interaction)
    await db.commit()
    if status == "success" and is_indexable_user_message(message):
        enqueue_memory_source_index(
            source_type=CONVERSATION_SOURCE,
            source_id=interaction.id,
            user_id=user_id,
        )
    return ChatResponse(
        intent=intent,
        message=final_message,
        suggested_actions=[],
        conversation_id=conversation.id,
        pending_action_id=pending_action_id,
        pending_action_summary=pending_action_summary,
        memory_sources=coaching.memory_sources,
    )
