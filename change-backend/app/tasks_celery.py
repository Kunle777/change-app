import asyncio
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from celery_app import celery_app
from app.database import AsyncSessionLocal
from app.tasks.models import Task, RecurrenceEnum
from app.tasks.schemas import TaskCreate
from app.tasks.service import get_completed_recurring_tasks, create_task
from sqlalchemy import select, and_


async def get_due_reminders(db):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    result = await db.execute(
        select(Task).where(
            and_(
                Task.reminder_time <= now,
                Task.is_reminder_sent == False,
                Task.status != "completed",
            )
        )
    )
    return result.scalars().all()


async def _check_reminders_async():
    async with AsyncSessionLocal() as db:
        due_tasks = await get_due_reminders(db)
        for task in due_tasks:
            print(f"REMINDER: Task '{task.title}' is due now for user {task.user_id}")
            task.is_reminder_sent = True
        await db.commit()


@celery_app.task
def check_reminders():
    asyncio.run(_check_reminders_async())


async def _spawn_recurring_async():
    async with AsyncSessionLocal() as db:
        tasks = await get_completed_recurring_tasks(db)
        for task in tasks:
            base = task.completed_at.replace(tzinfo=None) if task.completed_at.tzinfo else task.completed_at
            if task.recurrence == RecurrenceEnum.daily:
                next_due = base + relativedelta(days=1)
            elif task.recurrence == RecurrenceEnum.weekly:
                next_due = base + relativedelta(weeks=1)
            else:  # monthly
                next_due = base + relativedelta(months=1)

            await create_task(
                db,
                TaskCreate(
                    title=task.title,
                    priority=task.priority,
                    description=task.description,
                    recurrence=task.recurrence,
                    due_date=next_due,
                ),
                task.user_id,
            )
            task.recurrence_processed = True

        await db.commit()


@celery_app.task
def spawn_recurring_tasks():
    asyncio.run(_spawn_recurring_async())


@celery_app.task
def say_hello(name: str):
    print(f"Sending hello to {name}")
    return f"Hello, {name}!"
