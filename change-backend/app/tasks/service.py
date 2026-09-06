import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from app.tasks.models import Task, StatusEnum, RecurrenceEnum
from app.tasks.schemas import TaskCreate, TaskResponse, TaskUpdate
from datetime import datetime, timedelta,timezone
from app.ai import gemini
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import selectinload

def _utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.astimezone(timezone.utc)

async def create_task(db: AsyncSession, task_data: TaskCreate, user_id: uuid.UUID):
    recurrence = task_data.recurrence.name if task_data.recurrence else None
    db_task = Task(
        user_id=user_id,
        title=task_data.title,
        priority=task_data.priority,
        status=task_data.status,
        description=task_data.description,
        due_date=_utc(task_data.due_date),
        reminder_time=_utc(task_data.reminder_time),
        recurrence=recurrence,
    )
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)
    return db_task

async def get_tasks_for_user(db: AsyncSession, user_id: uuid.UUID):
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    result = await db.execute(
        select(Task).where(
            Task.user_id == user_id,
            or_(
                Task.status != StatusEnum.completed,
                Task.completed_at >= cutoff
            )
        )
    )
    return result.scalars().all()

async def get_task_by_id(db: AsyncSession, task_id: uuid.UUID, user_id: uuid.UUID):
    result = await db.execute(
        select(Task).where(
            Task.id == task_id,
            Task.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()
    
async def update_task(db: AsyncSession, task_id: uuid.UUID, task_data: TaskUpdate, user_id: uuid.UUID):
    db_task = await get_task_by_id(db, task_id, user_id)
    if not db_task:
        return None
    
    update_data = task_data.model_dump(exclude_unset=True)
    for var, value in update_data.items():
        if var == "recurrence" and value is not None:
            value = value.name
        if var in ("due_date", "reminder_time") and value is not None:
            value = _utc(value)
        setattr(db_task, var, value)
    
    await db.commit()
    await db.refresh(db_task)
    return db_task

async def delete_task(db: AsyncSession, task_id: uuid.UUID, user_id: uuid.UUID):
    db_task = await get_task_by_id(db, task_id, user_id)
    if not db_task:
        return None
    
    await db.delete(db_task)
    await db.commit()
    return db_task


async def snooze_task(db: AsyncSession, task_id: uuid.UUID, user_id: uuid.UUID):
    db_task = await get_task_by_id(db, task_id, user_id)
    if not db_task:
        return None

    db_task.reminder_time = datetime.now(timezone.utc) + timedelta(minutes=10)

    await db.commit()
    await db.refresh(db_task)
    return db_task


async def get_overdue_tasks(db: AsyncSession, user_id: uuid.UUID):
    current_time = datetime.now(timezone.utc)
    result = await db.execute(
        select(Task).where(
            and_(
                Task.user_id == user_id,
                Task.due_date < current_time,
                Task.status != StatusEnum.completed
            )
        )
    )
    overdue_task = result.scalars().all()
    return overdue_task

async def get_due_reminders(db: AsyncSession):
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Task)
        .options(selectinload(Task.user))
        .where(
            Task.reminder_time <= now,
            Task.is_reminder_sent == False,
            Task.status != StatusEnum.completed,
        )
    )
    return result.scalars().all()

async def breakdown_task(db: AsyncSession, task_id: uuid.UUID, user_id: uuid.UUID):
    task = await get_task_by_id(db, task_id, user_id)
    if task is  None:
        raise ValueError("Task not found ")


    prompt = (
        f"Break the following task into 3-6 small, concrete, actionable steps. "
        f"Task title: {task.title}\n"
        f"Task description: {task.description or 'No description provided'}\n"
        f"Respond with ONLY a JSON array of strings, each string one step. "
        f"No extra text, no markdown formatting."
    )
   
    steps = gemini.generate_structured(prompt)
    return steps

async def get_completed_recurring_tasks(db: AsyncSession):
    result = await db.execute(
        select(Task).where(
            Task.status == StatusEnum.completed,
            Task.completed_at.isnot(None),
            Task.recurrence.isnot(None),
            Task.recurrence != RecurrenceEnum.none,
            Task.recurrence_processed == False,
        )
    )
    return result.scalars().all()


async def mark_task_completed(db: AsyncSession, task_id: uuid.UUID, user_id: uuid.UUID):
    task = await get_task_by_id(db, task_id, user_id)
    if not task:
        return None
    task.status = StatusEnum.completed
    task.completed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(task)
    return task
