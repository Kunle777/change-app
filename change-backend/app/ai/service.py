import asyncio
import json
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.checkins import service as checkin_service
from app.ai.models import AIUsageLog
from app.ai import gemini
from app.ai.prompt_builder import build_prompt, build_system_prompt_for_user
from app.ai.freshness_service import resolve_user_timezone
from app.ai.context_builder import build_context
from app.ai.schemas import ChatResponse, ConversationDetail, ConversationSummary, ConversationTurn
from app.ai.intent_router import detect_intent
from app.ai.models import AIInteraction, Conversation
from app.ai import action_service
from app.memory.retrieval import memory_prompt_section, retrieve_memories, to_sources
from app.users.models import User

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


async def _handle_chat_legacy(db: AsyncSession, user_id, message: str) -> ChatResponse:
    if len(message) > 2000:
        raise ValueError("Message too long")

    intent = detect_intent(message)
    context = await build_context(db, user_id, intent)
    system_prompt, freshness = await build_system_prompt_for_user(
        db,
        user_id,
        intent,
        context,
        additional_instructions=(
            "Return only a valid JSON object with string fields 'intent' and 'message' "
            "and a 'suggested_actions' array."
        ),
    )
    prompt = build_prompt(system_prompt, message)

    raw = await asyncio.to_thread(gemini.generate_response, prompt)

    try:
        parsed = json.loads(raw)
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
            context_richness=freshness.tier.value,
            status="success",
        )
    )
    await db.commit()

    return response


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


async def _recent_conversation_history(
    db: AsyncSession, user_id: UUID, conversation_id: UUID
) -> str:
    # Seven prior turns represent at most 14 history messages; the current prompt adds message 15.
    result = await db.execute(
        select(AIInteraction)
        .where(
            AIInteraction.user_id == user_id,
            AIInteraction.conversation_id == conversation_id,
        )
        .order_by(AIInteraction.created_at.desc())
        .limit(7)
    )
    turns = list(result.scalars().all())
    turns.reverse()
    if not turns:
        return "No earlier messages in this conversation."
    lines = []
    for turn in turns:
        lines.extend((f"User: {turn.question}", f"ELVYN: {turn.response}"))
    return "\n".join(lines)


async def _handle_chat_without_tools(
    db: AsyncSession,
    user_id: UUID,
    message: str,
    conversation_id: UUID | None = None,
    timezone_name: str | None = None,
) -> ChatResponse:
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

    intent = detect_intent(message)
    context = await build_context(db, user_id, intent)
    history = await _recent_conversation_history(db, user_id, conversation.id)
    system_prompt, freshness = await build_system_prompt_for_user(
        db,
        user_id,
        intent,
        context,
        timezone_name=timezone_name,
        additional_instructions=(
            "Return only a valid JSON object with string fields 'intent' and 'message' "
            "and a 'suggested_actions' array."
        ),
    )
    prompt = build_prompt(system_prompt, message, history)
    raw = await asyncio.to_thread(gemini.generate_response, prompt)

    try:
        parsed = json.loads(raw)
        response = ChatResponse(
            intent=parsed.get("intent", intent),
            message=parsed.get("message", "Sorry, I couldn't process that."),
            suggested_actions=parsed.get("suggested_actions", []),
            conversation_id=conversation.id,
        )
    except Exception:
        response = ChatResponse(
            intent="general_coaching",
            message="I had trouble understanding that �? could you rephrase?",
            suggested_actions=[],
            conversation_id=conversation.id,
        )

    conversation.updated_at = datetime.now(timezone.utc)
    db.add(
        AIInteraction(
            user_id=user_id,
            conversation_id=conversation.id,
            intent=response.intent,
            question=message,
            response=response.message,
            context_used=context,
            context_size=len(context),
            context_richness=freshness.tier.value,
            status="success",
        )
    )
    await db.commit()
    return response


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

    intent = detect_intent(message)
    context = await build_context(db, user_id, intent)
    history_result = await db.execute(
        select(AIInteraction)
        .where(
            AIInteraction.user_id == user_id,
            AIInteraction.conversation_id == conversation.id,
        )
        .order_by(AIInteraction.created_at.desc())
        .limit(7)
    )
    previous_turns = list(history_result.scalars().all())
    previous_turns.reverse()
    history = [
        {"question": turn.question, "response": turn.response}
        for turn in previous_turns
    ]

    tz = user.last_active_timezone
    previous_q = previous_turns[-1].question if previous_turns else None
    memory = await retrieve_memories(
        db, user_id=user_id, question=message, intent=intent,
        previous_question=previous_q, tz_name=tz,
    )

    system_prompt, freshness = await build_system_prompt_for_user(
        db, user_id, intent, context, timezone_name=timezone_name,
        extra_context=memory_prompt_section(memory, tz_name=timezone_name),
    )
    generated = gemini.generate_chat_response_with_tools(system_prompt, history, message)

    pending_action_id = None
    pending_action_summary = None
    tool_call = generated.get("tool_call")
    if tool_call is None:
        final_message = generated.get("text") or "I couldn't finish that response."
    else:
        tool_name = tool_call.get("name")
        arguments = tool_call.get("args") or {}
        outcome = await action_service.handle_tool_call(
            db,
            user=user,
            conversation_id=conversation.id,
            tool_name=tool_name,
            arguments=arguments,
        )
        if outcome.get("status") == "awaiting_confirmation":
            pending_action_id = UUID(outcome["pending_action_id"])
            pending_action_summary = outcome["summary"]
            try:
                gemini.send_tool_result(generated["chat"], tool_name, outcome)
            except Exception:
                pass
            final_message = (
                f"I haven't changed anything yet. {pending_action_summary} "
                "Please confirm or reject it below."
            )
        else:
            try:
                final_message = gemini.send_tool_result(
                    generated["chat"], tool_name, outcome
                )
            except Exception:
                if outcome.get("status") == "created":
                    final_message = f"Created task: {outcome.get('title', 'your task')}."
                elif outcome.get("status") == "error":
                    final_message = f"I couldn't make that change: {outcome.get('reason', 'the request was invalid')}."
                else:
                    final_message = "The task action completed."

    conversation.updated_at = datetime.now(timezone.utc)
    db.add(
        AIInteraction(
            user_id=user_id,
            conversation_id=conversation.id,
            pending_action_id=pending_action_id,
            intent=intent,
            question=message,
            response=final_message,
            context_used=context,
            context_size=len(context),
            context_richness=freshness.tier.value,
            status="success",
        )
    )
    await db.commit()
    return ChatResponse(
        intent=intent,
        message=final_message,
        suggested_actions=[],
        conversation_id=conversation.id,
        pending_action_id=pending_action_id,
        pending_action_summary=pending_action_summary,
        memory_sources=to_sources(memory.memories, tz),
    )
