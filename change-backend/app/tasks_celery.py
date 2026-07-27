import asyncio
from datetime import datetime, timezone
from celery_app import celery_app
from app.database import AsyncSessionLocal
from app.tasks.models import Task
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


@celery_app.task
def say_hello(name: str):
    print(f"Sending hello to {name}")
    return f"Hello, {name}!"
