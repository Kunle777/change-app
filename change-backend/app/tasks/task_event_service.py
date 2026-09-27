import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.tasks.models import TaskEvent, TaskEventOutbox, TaskEventType

logger = logging.getLogger(__name__)


async def log_task_event(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    event_type: TaskEventType,
    task_id: uuid.UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Enqueue a durable event inside a savepoint owned by the caller.

    The outbox row is committed with the caller's task changes. If enqueueing
    fails, only the savepoint rolls back and the task action can still commit.
    A Celery worker later copies the durable outbox row to task_events.
    """
    occurred_at = datetime.now(timezone.utc)
    try:
        async with db.begin_nested():
            previous_timeout = (await db.execute(text("SHOW statement_timeout"))).scalar_one()
            await db.execute(
                text("SELECT set_config('statement_timeout', :timeout, true)"),
                {"timeout": "500ms"},
            )
            db.add(
                TaskEventOutbox(
                    user_id=user_id,
                    task_id=task_id,
                    event_type=event_type.value,
                    occurred_at=occurred_at,
                    event_metadata=metadata or {},
                )
            )
            await db.flush()
            await db.execute(
                text("SELECT set_config('statement_timeout', :timeout, true)"),
                {"timeout": previous_timeout},
            )
    except IntegrityError as error:
        constraint = getattr(error.orig, "constraint_name", None)
        if constraint in {
            "uq_task_events_overdue_deadline",
            "uq_task_events_reminder_open_notification",
            "uq_task_events_reminder_scheduled_notification",
            "uq_task_event_outbox_overdue_deadline",
            "uq_task_event_outbox_reminder_open_notification",
            "uq_task_event_outbox_reminder_scheduled_notification",
        }:
            logger.debug("Duplicate task event %s for task %s", event_type.value, task_id)
        else:
            logger.exception(
                "Task event insert failed its integrity constraint for user %s (task %s)",
                user_id,
                task_id,
            )
    except Exception:
        logger.exception(
            "Failed to log task event %s for user %s (task %s); task action can still commit",
            event_type.value,
            user_id,
            task_id,
        )


async def deliver_task_event_outbox(db: AsyncSession, limit: int = 100) -> int:
    """Move queued events into the append-only log, retaining failed rows to retry."""
    result = await db.execute(
        select(TaskEventOutbox)
        .order_by(TaskEventOutbox.created_at)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    outbox_rows = result.scalars().all()
    delivered = 0

    for outbox in outbox_rows:
        try:
            async with db.begin_nested():
                previous_timeout = (await db.execute(text("SHOW statement_timeout"))).scalar_one()
                await db.execute(
                    text("SELECT set_config('statement_timeout', :timeout, true)"),
                    {"timeout": "500ms"},
                )
                db.add(
                    TaskEvent(
                        id=outbox.id,
                        task_id=outbox.task_id,
                        user_id=outbox.user_id,
                        event_type=outbox.event_type,
                        occurred_at=outbox.occurred_at,
                        event_metadata=outbox.event_metadata,
                    )
                )
                await db.flush()
                await db.delete(outbox)
                await db.flush()
                await db.execute(
                    text("SELECT set_config('statement_timeout', :timeout, true)"),
                    {"timeout": previous_timeout},
                )
            delivered += 1
        except IntegrityError as error:
            constraint = getattr(error.orig, "constraint_name", None)
            if constraint in {
                "uq_task_events_overdue_deadline",
                "uq_task_events_reminder_open_notification",
                "uq_task_events_reminder_scheduled_notification",
                "task_events_pkey",
            }:
                # The destination already has the logical event; discard the duplicate queue item.
                await db.delete(outbox)
                delivered += 1
            else:
                outbox.attempts += 1
                outbox.last_error = type(error).__name__
                logger.warning("Task event %s remains queued after an integrity error", outbox.id)
        except Exception as error:
            outbox.attempts += 1
            outbox.last_error = type(error).__name__[:100]
            logger.warning("Task event %s remains queued after delivery failure", outbox.id)

    await db.commit()
    return delivered
