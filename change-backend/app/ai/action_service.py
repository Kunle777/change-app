import uuid
import logging
import hashlib
import hmac
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.models import PendingAction, PendingActionStatus
from app.ai.safe_text import redact_internal_identifiers
from app.ai.tool_executor import (
    AUTO_EXECUTE_TOOLS,
    CONFIRMATION_REQUIRED_TOOLS,
    execute_tool,
    validate_confirmation_tool,
)
from app.users.models import User


PENDING_ACTION_TTL = timedelta(minutes=10)
ACTION_REFERENCE_PREFIX = "pa_"
_ACTION_REFERENCE_PATTERN = re.compile(r"^pa_[0-9a-f]{64}$")
logger = logging.getLogger(__name__)


def opaque_action_reference(user_id: uuid.UUID, pending_id: uuid.UUID) -> str:
    digest = hashlib.sha256(f"{user_id}:{pending_id}".encode()).hexdigest()
    return f"{ACTION_REFERENCE_PREFIX}{digest}"


async def resolve_action_reference(
    db: AsyncSession, user: User, reference: str
) -> uuid.UUID | None:
    if not _ACTION_REFERENCE_PATTERN.fullmatch(reference):
        return None
    result = await db.execute(
        select(PendingAction.id)
        .where(
            PendingAction.user_id == user.id,
            PendingAction.created_at >= datetime.now(timezone.utc) - timedelta(days=30),
        )
        .order_by(PendingAction.created_at.desc())
        .limit(500)
    )
    for pending_id in result.scalars().all():
        if hmac.compare_digest(reference, opaque_action_reference(user.id, pending_id)):
            return pending_id
    return None


async def handle_tool_call(
    db: AsyncSession,
    user: User,
    conversation_id: uuid.UUID,
    tool_name: str,
    arguments: dict,
    *,
    eligible: bool = False,
    force_confirmation: bool = False,
    request_message: str | None = None,
) -> dict:
    """Run one model-proposed tool call.

    `force_confirmation` stages even auto-execute tools (create_task) as pending actions.
    It is set whenever untrusted context was supplied to the model.
    """
    if not eligible or tool_name not in AUTO_EXECUTE_TOOLS | CONFIRMATION_REQUIRED_TOOLS:
        return {"status": "error", "reason": "Action is not available for this request"}

    if tool_name in CONFIRMATION_REQUIRED_TOOLS or (
        force_confirmation and tool_name in AUTO_EXECUTE_TOOLS
    ):
        try:
            validated = await validate_confirmation_tool(
                db,
                user,
                tool_name,
                arguments,
                request_message=request_message,
            )
        except ValueError as error:
            return {"status": "error", "reason": str(error)}
        if isinstance(validated, dict):
            return validated
        safe_arguments, summary = validated
        pending = PendingAction(
            user_id=user.id,
            conversation_id=conversation_id,
            tool_name=tool_name,
            summary=summary,
            arguments=safe_arguments,
            status=PendingActionStatus.PENDING.value,
            expires_at=datetime.now(timezone.utc) + PENDING_ACTION_TTL,
        )
        db.add(pending)
        await db.flush()
        return {
            "status": "awaiting_confirmation",
            "pending_action_id": str(pending.id),
            "summary": pending.summary,
        }

    try:
        outcome = await execute_tool(
            db, user, tool_name, arguments, request_message=request_message
        )
    except ValueError as error:
        return {"status": "error", "reason": str(error)}
    return outcome


async def list_pending_actions(
    db: AsyncSession, user: User, conversation_id: uuid.UUID
) -> list[dict]:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(PendingAction)
        .where(
            PendingAction.user_id == user.id,
            PendingAction.conversation_id == conversation_id,
        )
        .order_by(PendingAction.created_at.desc())
        .limit(50)
    )
    actions = list(result.scalars().all())
    expired = False
    for action in actions:
        if (
            action.status == PendingActionStatus.PENDING.value
            and now >= action.expires_at
        ):
            action.status = PendingActionStatus.EXPIRED.value
            action.outcome = {"status": PendingActionStatus.EXPIRED.value}
            expired = True
    if expired:
        await db.commit()
    return [
        {
            "id": opaque_action_reference(user.id, action.id),
            "summary": redact_internal_identifiers(action.summary),
            "expires_at": action.expires_at,
            "status": (
                action.outcome.get("status")
                if action.status == PendingActionStatus.CONFIRMED.value and action.outcome
                else action.status
            ),
        }
        for action in reversed(actions)
    ]


async def confirm_pending_action(
    db: AsyncSession, user: User, pending_id: uuid.UUID, *, commit: bool = True
) -> dict:
    result = await db.execute(
        select(PendingAction)
        .where(
            PendingAction.id == pending_id,
            PendingAction.user_id == user.id,
        )
        .with_for_update()
    )
    pending = result.scalar_one_or_none()
    if pending is None:
        return {"status": "error", "reason": "No matching pending action"}

    if pending.status != PendingActionStatus.PENDING.value:
        if pending.outcome:
            return {"status": pending.outcome.get("status", "error"), "already_resolved": True}
        return {"status": "error", "reason": "This action is no longer available"}

    if datetime.now(timezone.utc) >= pending.expires_at:
        pending.status = PendingActionStatus.EXPIRED.value
        pending.outcome = {"status": PendingActionStatus.EXPIRED.value}
        if commit:
            await db.commit()
        return {"status": "expired", "reason": "This action expired; ask again."}

    try:
        outcome = await execute_tool(db, user, pending.tool_name, pending.arguments)
        if outcome.get("status") == "error":
            await db.rollback()
            return {"status": "error", "retryable": True}
        if outcome.get("status") == "stale":
            pending.status = PendingActionStatus.STALE.value
            pending.outcome = {"status": PendingActionStatus.STALE.value}
            if commit:
                await db.commit()
            return {"status": PendingActionStatus.STALE.value}
        pending.status = PendingActionStatus.CONFIRMED.value
        pending.outcome = {
            "status": outcome.get("status", "error"),
            **(
                {"title": redact_internal_identifiers(outcome["title"])}
                if isinstance(outcome.get("title"), str)
                else {}
            ),
        }
        if commit:
            await db.commit()
        return dict(pending.outcome)
    except Exception as error:
        # Roll back both the task mutation and the pending status if anything fails.
        await db.rollback()
        logger.error(
            "Pending action execution failed category=%s",
            type(error).__name__,
        )
        raise


async def reject_pending_action(
    db: AsyncSession, user: User, pending_id: uuid.UUID, *, commit: bool = True
) -> dict:
    result = await db.execute(
        select(PendingAction)
        .where(
            PendingAction.id == pending_id,
            PendingAction.user_id == user.id,
            PendingAction.status == PendingActionStatus.PENDING.value,
        )
        .with_for_update()
    )
    pending = result.scalar_one_or_none()
    if pending is None:
        return {"status": "error", "reason": "No matching pending action"}

    if datetime.now(timezone.utc) >= pending.expires_at:
        pending.status = PendingActionStatus.EXPIRED.value
        pending.outcome = {"status": PendingActionStatus.EXPIRED.value}
        if commit:
            await db.commit()
        return {"status": "expired", "reason": "This action expired; ask again."}

    pending.status = PendingActionStatus.REJECTED.value
    pending.outcome = {"status": PendingActionStatus.REJECTED.value}
    if commit:
        await db.commit()
    return {"status": "rejected"}
