import asyncio
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from celery_app import celery_app
from app.database import AsyncSessionLocal, AsyncSession
from app.tasks.models import Task, RecurrenceEnum, TaskEvent, TaskEventOutbox
from app.tasks.schemas import TaskCreate
from app.tasks.service import (
    get_completed_recurring_tasks,
    create_task,
    get_due_reminders,
    record_overdue_task_events as record_overdue_events,
)
from app.tasks.task_event_service import deliver_task_event_outbox
from app.tasks.recurrence_service import generate_recurring_task_occurrences
from app.tasks.models import TaskEventType
from app.tasks.task_event_service import log_task_event
from sqlalchemy import select, and_
from fcm import send_push_notification
from app.savings.service import check_and_process_matured_vaults


async def _check_reminders_async():
    async with AsyncSessionLocal() as db:
        due_tasks = await get_due_reminders(db)
        for task in due_tasks:
            local_scheduled = False
            if task.reminder_time is not None:
                expected = task.reminder_time
                if expected.tzinfo is None:
                    expected = expected.replace(tzinfo=timezone.utc)
                for event_model in (TaskEvent, TaskEventOutbox):
                    result = await db.execute(
                        select(event_model.event_metadata["reminder_time"].astext).where(
                            event_model.task_id == task.id,
                            event_model.event_type == TaskEventType.REMINDER_SCHEDULED.value,
                        )
                    )
                    for raw_time in result.scalars().all():
                        if not raw_time:
                            continue
                        try:
                            scheduled_time = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
                            if scheduled_time.tzinfo is None:
                                scheduled_time = scheduled_time.replace(tzinfo=timezone.utc)
                            if scheduled_time.astimezone(timezone.utc) == expected.astimezone(timezone.utc):
                                local_scheduled = True
                                break
                        except ValueError:
                            continue
                    if local_scheduled:
                        break

            if local_scheduled:
                # Expo owns this reminder on-device; skip FCM to avoid duplicate alerts.
                task.is_reminder_sent = True
            elif task.user and task.user.fcm_token:
                try:
                    send_push_notification(
                        task.user.fcm_token,
                        title="Task Reminder",
                        body=task.title,
                    )
                    task.is_reminder_sent = True
                except Exception as e:
                    print(f"FCM send failed for task {task.id}: {e}")
            else:
                print(f"No FCM token for task {task.id}, user={task.user_id}")
        await db.commit()


@celery_app.task
def check_reminders():
    asyncio.run(_check_reminders_async())


async def _record_overdue_task_events_async():
    async with AsyncSessionLocal() as db:
        await record_overdue_events(db)


@celery_app.task
def record_overdue_task_events_job():
    asyncio.run(_record_overdue_task_events_async())


async def _deliver_task_event_outbox_async():
    async with AsyncSessionLocal() as db:
        await deliver_task_event_outbox(db)


@celery_app.task
def deliver_task_event_outbox_job():
    asyncio.run(_deliver_task_event_outbox_async())


async def _spawn_recurring_async(db: AsyncSession):
    # New recurring tasks are generated ahead in a bounded, idempotent window.
    await generate_recurring_task_occurrences(db, horizon_days=30)

    # Preserve older recurrence rows created before task_series existed.
    legacy_tasks = await get_completed_recurring_tasks(db)
    for task in legacy_tasks:
        base = task.due_date or task.completed_at
        if base.tzinfo is None:
            base = base.replace(tzinfo=timezone.utc)
        if task.recurrence == "daily":
            next_due = base + relativedelta(days=1)
            next_reminder = task.reminder_time + relativedelta(days=1) if task.reminder_time else None
        elif task.recurrence == "weekly":
            next_due = base + relativedelta(weeks=1)
            next_reminder = task.reminder_time + relativedelta(weeks=1) if task.reminder_time else None
        else:
            next_due = base + relativedelta(months=1)
            next_reminder = task.reminder_time + relativedelta(months=1) if task.reminder_time else None
        from app.tasks.models import Task, StatusEnum
        next_task = Task(
            user_id=task.user_id,
            title=task.title,
            description=task.description,
            priority=task.priority,
            status=StatusEnum.pending,
            recurrence=task.recurrence,
            due_date=next_due,
            reminder_time=next_reminder,
        )
        db.add(next_task)
        await db.flush()
        await log_task_event(db, user_id=task.user_id, task_id=next_task.id, event_type=TaskEventType.CREATED)
        task.recurrence_processed = True
    await db.commit()


async def _spawn_recurring_tasks_async():
    async with AsyncSessionLocal() as db:
        await _spawn_recurring_async(db)


@celery_app.task
def spawn_recurring_task_job():
    asyncio.run(_spawn_recurring_tasks_async())


@celery_app.task
def say_hello(name: str):
    print(f"Sending hello to {name}")
    return f"Hello, {name}!"

@celery_app.task
def process_matured_vaults():
    asyncio.run(check_and_process_matured_vaults())
