import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.models import PendingAction, PendingActionStatus
from app.ai.tool_executor import (
    AUTO_EXECUTE_TOOLS,
    CONFIRMATION_REQUIRED_TOOLS,
    execute_tool,
    validate_confirmation_tool,
)
from app.users.models import User


PENDING_ACTION_TTL = timedelta(minutes=10)


async def handle_tool_call(
    db: AsyncSession,
    user: User,
    conversation_id: uuid.UUID,
    tool_name: str,
    arguments: dict,
) -> dict:
    if tool_name in CONFIRMATION_REQUIRED_TOOLS:
        try:
            validated = await validate_confirmation_tool(db, user, tool_name, arguments)
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
        await db.commit()
        return {
            "status": "awaiting_confirmation",
            "pending_action_id": str(pending.id),
            "summary": pending.summary,
        }

    if tool_name not in AUTO_EXECUTE_TOOLS:
        return {"status": "error", "reason": f"Unknown tool: {tool_name}"}

    try:
        outcome = await execute_tool(db, user, tool_name, arguments)
    except ValueError as error:
        return {"status": "error", "reason": str(error)}
    await db.commit()
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
            PendingAction.status == PendingActionStatus.PENDING.value,
            PendingAction.expires_at > now,
        )
        .order_by(PendingAction.created_at.asc())
    )
    return [
        {
            "id": str(action.id),
            "summary": action.summary,
            "expires_at": action.expires_at,
        }
        for action in result.scalars().all()
    ]


async def confirm_pending_action(
    db: AsyncSession, user: User, pending_id: uuid.UUID
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
        await db.commit()
        return {"status": "expired", "reason": "This action expired; ask again."}

    try:
        outcome = await execute_tool(db, user, pending.tool_name, pending.arguments)
        if outcome.get("status") == "error":
            await db.rollback()
            return outcome
        if outcome.get("status") == "stale":
            pending.status = PendingActionStatus.STALE.value
            await db.commit()
            return outcome
        pending.status = PendingActionStatus.CONFIRMED.value
        await db.commit()
        return outcome
    except Exception:
        # Roll back both the task mutation and the pending status if anything fails.
        await db.rollback()
        raise


async def reject_pending_action(
    db: AsyncSession, user: User, pending_id: uuid.UUID
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
        await db.commit()
        return {"status": "expired", "reason": "This action expired; ask again."}

    pending.status = PendingActionStatus.REJECTED.value
    await db.commit()
    return {"status": "rejected"}
