import asyncio
import logging
import re
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.checkins import service as checkin_service
from app.ai.models import AIUsageLog
from app.ai import gemini
from app.ai.prompt_builder import build_system_prompt_for_user
from app.ai.freshness_service import resolve_user_timezone
from app.ai.context_service import assemble_coaching_context
from app.ai.schemas import ChatResponse, ConversationDetail, ConversationSummary, ConversationTurn

from app.ai.models import AIInteraction, Conversation, PendingAction
from app.ai import action_service
from app.ai.errors import AIRequestError, classify_ai_failure
from app.ai.safe_text import redact_internal_identifiers
from app.memory.sources import CONVERSATION_SOURCE, is_indexable_user_message
from app.memory.tasks import enqueue_memory_source_index
from app.users.models import User

logger = logging.getLogger(__name__)
_INTERNAL_RESPONSE_MARKER = re.compile(
    r"\btool note\s*:|no task tools are available this turn|"
    r"\bsystem[_ ](?:instruction|prompt)\b|\bfunction[_ ]call\b|"
    r"\btool[_ ](?:call|result|instructions?)\b|"
    r"do not say or imply that you|<saved_entries>",
    re.I,
)
_AFFIRMATIVE = re.compile(
    r"^(yes|yeah|yep|sure|confirm|do it|go ahead|proceed|please do|ok|okay)[.! ]*$",
    re.I,
)
_NEGATIVE = re.compile(
    r"^(no|nope|reject|cancel|cancel that|never mind|nevermind|don't|do not)[.! ]*$",
    re.I,
)
_AMBIGUOUS_CONFIRMATION = re.compile(r"^(yes|yeah|yep|sure|ok|okay|no|nope)\b", re.I)
_IDENTIFIER_REQUEST = re.compile(
    r"\b(?:show|tell|give|reveal|include|print|display|expose|what(?:'s| is))\b"
    r".{0,80}\b(?:primary key|(?:task|database|internal|pending[- ]action|tool[- ]call)?"
    r"\s*(?:id|identifier|number))\b"
    r"|\b(?:task|database|internal|primary key|pending[- ]action|tool[- ]call)"
    r"\s*(?:id|identifier|number)\b",
    re.I,
)
_ACTION_SUCCESS_CLAIM = re.compile(
    r"\b(?:i (?:did|have|ve|just|already)|done|successfully|it's been|it has been)"
    r"\b.{0,50}\b(created|added|scheduled|rescheduled|moved|changed|updated|cancelled|deleted)\b"
    r"|\bi (?:created|added|scheduled|rescheduled|moved|changed|updated|cancelled|deleted)\b"
    r"|\b(?:the task|it)\s+(?:has been|was|is)\s+"
    r"(?:created|added|scheduled|rescheduled|moved|changed|updated|cancelled|deleted)\b"
    r"|\b(?:created|added|scheduled|rescheduled|moved|changed|updated|cancelled|deleted)"
    r"\s+(?:the|your)\s+task\b",
    re.I,
)


def sanitize_assistant_response(text: str | None) -> str:
    value = redact_internal_identifiers((text or "").strip())
    if not value or _INTERNAL_RESPONSE_MARKER.search(value):
        return "I'm here to help with your tasks. What would you like to do?"
    return value


def _safe_model_response(text: str | None, *, action_requested: bool) -> str:
    value = sanitize_assistant_response(text)
    if _ACTION_SUCCESS_CLAIM.search(value):
        if action_requested:
            return "I haven't changed anything yet. What date, time, or other details should I use?"
        return "I can help with that. Tell me what you would like to do next."
    return value


def _action_response(outcome: dict) -> str:
    status = outcome.get("status")
    if status == "awaiting_confirmation":
        return (
            f"I haven't changed anything yet. "
            f"{sanitize_assistant_response(outcome['summary'])} "
            "Please confirm or reject it below, or reply Yes or No."
        )
    if status == "ambiguous":
        choices = []
        for item in outcome.get("candidates", []):
            title = sanitize_assistant_response(item.get("title"))
            details = [title, item.get("status")]
            if item.get("deadline"):
                details.append(sanitize_assistant_response(item["deadline"]))
            choices.append(" — ".join(part for part in details if part))
        return (
            "I found more than one open task that could match: "
            + "; ".join(choices)
            + ". Which one should I use?"
        )
    title = outcome.get("title")
    task_reference = (
        f' "{sanitize_assistant_response(title)}"' if isinstance(title, str) else " the task"
    )
    return {
        "created": f"Done — I added{task_reference}.",
        "updated": f"Done — I updated{task_reference}.",
        "cancelled": f"Done — I cancelled{task_reference}.",
        "rejected": "No problem. Nothing was changed.",
        "expired": "That confirmation expired. Ask me to prepare the task change again.",
        "stale": "That task changed after the proposal. Ask me to prepare a fresh change.",
        "not_found": "I couldn't find an open task matching that name in your tasks.",
        "error": (
            "I couldn't safely make that task change. Please check the task and requested "
            "date or time, then try again."
        ),
    }.get(status, "I couldn't safely complete that task action. Please try again.")


def _confirmation_choice(message: str) -> bool | None:
    text = " ".join((message or "").strip().lower().split())
    if _AFFIRMATIVE.fullmatch(text):
        return True
    if _NEGATIVE.fullmatch(text):
        return False
    return None


async def _find_idempotent_interaction(
    db: AsyncSession, user_id: UUID, idempotency_key: UUID
) -> AIInteraction | None:
    result = await db.execute(
        select(AIInteraction).where(
            AIInteraction.user_id == user_id,
            AIInteraction.idempotency_key == idempotency_key,
        )
    )
    return result.scalar_one_or_none()


async def _response_for_saved_interaction(
    db: AsyncSession, interaction: AIInteraction
) -> ChatResponse:
    pending_summary = None
    if interaction.pending_action_id:
        result = await db.execute(
            select(PendingAction).where(
                PendingAction.id == interaction.pending_action_id,
                PendingAction.user_id == interaction.user_id,
            )
        )
        action = result.scalar_one_or_none()
        pending_summary = (
            sanitize_assistant_response(action.summary) if action else None
        )
    return ChatResponse(
        intent=interaction.intent or "general_coaching",
        message=sanitize_assistant_response(interaction.response),
        conversation_id=interaction.conversation_id,
        pending_action_id=(
            action_service.opaque_action_reference(
                interaction.user_id, interaction.pending_action_id
            )
            if interaction.pending_action_id
            else None
        ),
        resolved_action_id=(
            action_service.opaque_action_reference(
                interaction.user_id, interaction.resolved_action_id
            )
            if interaction.resolved_action_id
            else None
        ),
        resolved_action_status=interaction.resolved_action_status,
        pending_action_summary=pending_summary,
        idempotent_replay=True,
    )


async def get_idempotent_chat_response(
    db: AsyncSession, user_id: UUID, idempotency_key: UUID | None
) -> ChatResponse | None:
    if idempotency_key is None:
        return None
    interaction = await _find_idempotent_interaction(db, user_id, idempotency_key)
    if interaction is None:
        return None
    return await _response_for_saved_interaction(db, interaction)


async def _latest_interaction(
    db: AsyncSession, user_id: UUID, conversation_id: UUID
) -> AIInteraction | None:
    result = await db.execute(
        select(AIInteraction)
        .where(
            AIInteraction.user_id == user_id,
            AIInteraction.conversation_id == conversation_id,
        )
        .order_by(AIInteraction.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _commit_chat_interaction(
    db: AsyncSession, user_id: UUID, idempotency_key: UUID | None
) -> ChatResponse | None:
    try:
        await db.commit()
        return None
    except IntegrityError:
        await db.rollback()
        if idempotency_key is None:
            raise
        saved = await _find_idempotent_interaction(db, user_id, idempotency_key)
        if saved is None:
            raise
        return await _response_for_saved_interaction(db, saved)
    except Exception:
        await db.rollback()
        raise

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
        "",
        additional_instructions=(
            "Write a short, honest, encouraging 3-4 sentence summary noticing any "
            "patterns in mood or recurring themes. Do not invent details not present "
            "in the supplied check-in history."
        ),
    )
    response = await asyncio.to_thread(
        gemini.generate_response,
        system_prompt,
        context_payload=checkin_text,
    )
    return sanitize_assistant_response(response)



async def check_usage(db: AsyncSession, user_id) -> bool:
    today = date.today()
    result = await db.execute(
        select(AIUsageLog).where(
            AIUsageLog.user_id == user_id, AIUsageLog.usage_date == today
        )
    )
    log = result.scalar_one_or_none()
    DAILY_LIMIT = 500
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
            response=sanitize_assistant_response(item.response),
            intent=item.intent,
            created_at=item.created_at,
            pending_action_id=(
                action_service.opaque_action_reference(user_id, item.pending_action_id)
                if item.pending_action_id
                else None
            ),
            resolved_action_id=(
                action_service.opaque_action_reference(user_id, item.resolved_action_id)
                if item.resolved_action_id
                else None
            ),
            resolved_action_status=item.resolved_action_status,
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
    idempotency_key: UUID | None = None,
    request_id: str | None = None,
) -> ChatResponse:
    user_id = user.id
    request_id = request_id or str(UUID(int=0))
    if len(message) > 2000:
        raise ValueError("Message too long")

    if idempotency_key is not None:
        saved = await _find_idempotent_interaction(db, user_id, idempotency_key)
        if saved is not None:
            return await _response_for_saved_interaction(db, saved)

    if conversation_id is None:
        conversation = await get_or_create_active_conversation(
            db, user_id, message, timezone_name
        )
    else:
        conversation = await continue_conversation(db, user_id, conversation_id)
        if conversation is None:
            raise LookupError("Conversation not found")
    current_conversation_id = conversation.id
    conversation_title = getattr(conversation, "title", "New conversation")

    if _IDENTIFIER_REQUEST.search(message):
        response_text = (
            "I can't provide internal task or database identifiers. I can help find "
            "a task by its title and relevant details instead."
        )
        interaction = AIInteraction(
            user_id=user_id,
            conversation_id=conversation.id,
            intent="identifier_request",
            question=message,
            response=response_text,
            status="success",
            idempotency_key=idempotency_key,
        )
        db.add(interaction)
        replayed = await _commit_chat_interaction(db, user_id, idempotency_key)
        if replayed:
            return replayed
        return ChatResponse(
            intent="identifier_request",
            message=response_text,
            conversation_id=conversation.id,
        )

    latest = await _latest_interaction(db, user_id, conversation.id)
    latest_pending_action_id = None
    if latest:
        if latest.pending_action_id:
            latest_pending_action_id = latest.pending_action_id
        elif getattr(latest, "resolved_action_status", None) == "pending":
            latest_pending_action_id = getattr(latest, "resolved_action_id", None)
    if latest_pending_action_id:
        choice = _confirmation_choice(message)
        pending_result = await db.execute(
            select(PendingAction).where(
                PendingAction.id == latest_pending_action_id,
                PendingAction.user_id == user_id,
            )
        )
        pending = pending_result.scalar_one_or_none()
        if pending is None or pending.status != "pending":
            choice = None
            if _AMBIGUOUS_CONFIRMATION.match(message.strip()):
                final_message = "That proposal is no longer waiting for confirmation. Ask me to prepare it again if you still want the change."
                interaction = AIInteraction(
                    user_id=user_id,
                    conversation_id=conversation.id,
                    intent="task_action_confirmation",
                    question=message,
                    response=final_message,
                    status="success",
                    idempotency_key=idempotency_key,
                )
                db.add(interaction)
                replayed = await _commit_chat_interaction(
                    db, user_id, idempotency_key
                )
                if replayed:
                    return replayed
                return ChatResponse(
                    intent="task_action_confirmation",
                    message=final_message,
                    conversation_id=conversation.id,
                )
        if choice is not None:
            outcome = (
                await action_service.confirm_pending_action(
                    db, user, latest_pending_action_id, commit=False
                )
                if choice
                else await action_service.reject_pending_action(
                    db, user, latest_pending_action_id, commit=False
                )
            )
            retryable = outcome.get("retryable", False)
            resolved_status = "pending" if retryable else outcome.get("status")
            final_message = _action_response(outcome)
            interaction = AIInteraction(
                user_id=user_id,
                conversation_id=conversation.id,
                intent="task_action_confirmation",
                question=message,
                response=final_message,
                status="success" if outcome.get("status") != "error" else "error",
                tool_used=True,
                tool_name="confirm_pending_action" if choice else "reject_pending_action",
                resolved_action_id=latest_pending_action_id,
                resolved_action_status=resolved_status,
                idempotency_key=idempotency_key,
            )
            conversation.updated_at = datetime.now(timezone.utc)
            db.add(interaction)
            replayed = await _commit_chat_interaction(db, user_id, idempotency_key)
            if replayed:
                return replayed
            return ChatResponse(
                intent="task_action_confirmation",
                message=final_message,
                conversation_id=conversation.id,
                resolved_action_id=action_service.opaque_action_reference(
                    user_id, latest_pending_action_id
                ),
                resolved_action_status=resolved_status,
            )
        if _AMBIGUOUS_CONFIRMATION.match(message.strip()):
            final_message = "Please confirm or reject the proposed action using its buttons, or reply with a clear Yes or No."
            interaction = AIInteraction(
                user_id=user_id,
                conversation_id=conversation.id,
                intent="task_action_confirmation",
                question=message,
                response=final_message,
                status="success",
                idempotency_key=idempotency_key,
            )
            conversation.updated_at = datetime.now(timezone.utc)
            db.add(interaction)
            replayed = await _commit_chat_interaction(db, user_id, idempotency_key)
            if replayed:
                return replayed
            return ChatResponse(
                intent="task_action_confirmation",
                message=final_message,
                conversation_id=conversation.id,
            )

    identity_response = gemini.provider_identity_answer(message)
    if identity_response:
        conversation.updated_at = datetime.now(timezone.utc)
        interaction = AIInteraction(
            user_id=user_id,
            conversation_id=conversation.id,
            intent="provider_identity",
            question=message,
            response=identity_response,
            status="success",
            idempotency_key=idempotency_key,
        )
        db.add(interaction)
        replayed = await _commit_chat_interaction(db, user_id, idempotency_key)
        if replayed:
            return replayed
        return ChatResponse(
            intent="provider_identity",
            message=identity_response,
            conversation_id=conversation.id,
        )

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
            allowed_tool_names=coaching.allowed_tool_names,
            context_payload=coaching.context_payload,
        )
        tool_call = generated.get("tool_call")
        if tool_call is None:
            final_message = _safe_model_response(
                generated.get("text"), action_requested=coaching.plan.action_intent
            )
        else:
            raw_tool_name = tool_call.get("name")
            tool_name = raw_tool_name if isinstance(raw_tool_name, str) else ""
            tool_used = True
            tool_name_used = tool_name
            arguments = tool_call.get("args")
            if not isinstance(arguments, dict):
                arguments = {}
            outcome = await action_service.handle_tool_call(
                db,
                user=user,
                conversation_id=conversation.id,
                tool_name=tool_name,
                arguments=arguments,
                eligible=(
                    coaching.allow_tools
                    and tool_name in coaching.allowed_tool_names
                ),
                force_confirmation=coaching.require_confirmation,
                request_message=coaching.action_request_message,
            )
            if outcome.get("status") == "awaiting_confirmation":
                pending_action_id = UUID(outcome["pending_action_id"])
                pending_action_summary = sanitize_assistant_response(outcome["summary"])
                final_message = _action_response(outcome)
            else:
                status = outcome.get("status")
                if status in {"created", "updated", "cancelled"}:
                    final_message = _action_response(outcome)
                elif status == "error" and "due_date or priority" in outcome.get("reason", ""):
                    final_message = "What date and time, or priority, should I use for that task?"
                else:
                    final_message = _action_response(outcome)
    except Exception as error:
        await db.rollback()
        failure = classify_ai_failure(error)
        logger.error(
            "AI chat failed category=%s request_id=%s",
            failure.code,
            request_id,
        )
        raise AIRequestError(failure, request_id) from error

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
        idempotency_key=idempotency_key,
    )
    db.add(interaction)
    replayed = await _commit_chat_interaction(db, user_id, idempotency_key)
    if replayed:
        return replayed
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
        pending_action_id=(
            action_service.opaque_action_reference(user_id, pending_action_id)
            if pending_action_id
            else None
        ),
        pending_action_summary=pending_action_summary,
        memory_sources=coaching.memory_sources,
    )
