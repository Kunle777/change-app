import uuid
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from app.tasks.models import (
    Task,
    StatusEnum,
    RecurrenceEnum,
    TaskEvent,
    TaskEventOutbox,
    TaskEventType,
    TaskSeries,
    PriorityEnum,
)
from app.tasks.schemas import TaskCreate, TaskResponse, TaskUpdate, SeriesEditRequest
from app.ai import gemini
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import selectinload
from app.tasks.task_event_service import log_task_event
from app.tasks.recurrence_service import stop_task_series


async def edit_task_series(
    db: AsyncSession,
    task_id: uuid.UUID,
    user_id: uuid.UUID,
    edit: SeriesEditRequest,
):
    task = await get_task_by_id(db, task_id, user_id)
    if task is None:
        return None
    if task.series_id is None:
        return False

    series_result = await db.execute(
        select(TaskSeries).where(TaskSeries.id == task.series_id, TaskSeries.user_id == user_id).with_for_update()
    )
    series = series_result.scalar_one_or_none()
    if series is None:
        return False

    if edit.scope == "occurrence":
        targets = [task]
    else:
        query = select(Task).where(Task.series_id == series.id, Task.is_deleted.is_(False))
        if edit.scope == "this_and_future":
            query = query.where(
                Task.status == StatusEnum.pending,
                Task.occurrence_date >= task.occurrence_date,
            )
        target_result = await db.execute(query)
        targets = target_result.scalars().all()

        # Future generated occurrences inherit these values from the series.
        series.title = edit.title
        series.description = edit.description
        series.priority = edit.priority.name

    for occurrence in targets:
        occurrence.title = edit.title
        occurrence.description = edit.description
        occurrence.priority = edit.priority

    await db.commit()
    await db.refresh(task)
    return task

def _utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.astimezone(timezone.utc)

async def create_task(db: AsyncSession, task_data: TaskCreate, user_id: uuid.UUID):
    rule = task_data.recurrence_rule
    series = None
    if rule is not None:
        series = TaskSeries(
            user_id=user_id,
            title=task_data.title,
            description=task_data.description,
            priority=task_data.priority.name,
            frequency=rule.frequency,
            interval=rule.interval,
            days_of_week=rule.days_of_week,
            start_date=rule.start_date,
            local_time=rule.local_time,
            timezone=rule.timezone,
            end_date=rule.end_date,
            occurrence_limit=rule.occurrence_limit,
            generated_count=1,
            is_active=rule.occurrence_limit != 1,
        )
        db.add(series)
        await db.flush()

    recurrence = series.frequency if series else (task_data.recurrence.name if task_data.recurrence else None)
    due_date = task_data.due_date
    reminder_time = task_data.reminder_time
    if series:
        zone = ZoneInfo(series.timezone)
        due_date = datetime.combine(series.start_date, series.local_time or time.max, tzinfo=zone)
        if series.local_time is not None:
            reminder_time = datetime.combine(series.start_date, series.local_time, tzinfo=zone)
    db_task = Task(
        user_id=user_id,
        title=task_data.title,
        priority=task_data.priority,
        status=task_data.status,
        description=task_data.description,
        due_date=_utc(due_date),
        reminder_time=_utc(reminder_time),
        recurrence=recurrence,
        series_id=series.id if series else None,
        occurrence_date=series.start_date if series else None,
    )
    db.add(db_task)
    await db.flush()
    await log_task_event(
        db,
        user_id=user_id,
        task_id=db_task.id,
        event_type=TaskEventType.CREATED,
    )
    await db.commit()
    await db.refresh(db_task)
    return db_task

async def get_tasks_for_user(db: AsyncSession, user_id: uuid.UUID):
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    result = await db.execute(
        select(Task).where(
            Task.user_id == user_id,
            Task.is_deleted.is_(False),
            or_(
                Task.status != StatusEnum.completed,
                Task.completed_at >= cutoff,
            )
        )
    )
    return result.scalars().all()


async def get_upcoming_tasks(db: AsyncSession, user_id: uuid.UUID, days: int = 14):
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=days)
    result = await db.execute(
        select(Task).where(
            Task.user_id == user_id,
            Task.is_deleted.is_(False),
            Task.status == StatusEnum.pending,
            Task.reminder_time.is_not(None),
            Task.reminder_time >= now,
            Task.reminder_time <= end,
        )
    )
    return result.scalars().all()

async def get_task_by_id(db: AsyncSession, task_id: uuid.UUID, user_id: uuid.UUID):
    result = await db.execute(
        select(Task).where(
            Task.id == task_id,
            Task.user_id == user_id,
            Task.is_deleted.is_(False),
        )
    )
    return result.scalar_one_or_none()
    
async def update_task(db: AsyncSession, task_id: uuid.UUID, task_data: TaskUpdate, user_id: uuid.UUID):
    db_task = await get_task_by_id(db, task_id, user_id)
    if not db_task:
        return None
    
    old_due_date = db_task.due_date
    old_reminder_time = db_task.reminder_time
    old_status = db_task.status
    update_data = task_data.model_dump(exclude_unset=True)
    for var, value in update_data.items():
        if var == "recurrence" and value is not None:
            value = value.name
        if var in ("due_date", "reminder_time") and value is not None:
            value = _utc(value)
        setattr(db_task, var, value)

    if old_reminder_time != db_task.reminder_time:
        db_task.is_reminder_sent = False
    
    if old_status != StatusEnum.completed and db_task.status == StatusEnum.completed:
        await log_task_event(
            db,
            user_id=user_id,
            task_id=db_task.id,
            event_type=TaskEventType.COMPLETED,
        )
    elif old_status != StatusEnum.cancelled and db_task.status == StatusEnum.cancelled:
        await log_task_event(
            db,
            user_id=user_id,
            task_id=db_task.id,
            event_type=TaskEventType.CANCELLED,
        )
    if old_due_date != db_task.due_date:
        await log_task_event(
            db,
            user_id=user_id,
            task_id=db_task.id,
            event_type=TaskEventType.DEADLINE_CHANGED,
            metadata={
                "old_due": old_due_date.isoformat() if old_due_date else None,
                "new_due": db_task.due_date.isoformat() if db_task.due_date else None,
            },
        )
    if old_reminder_time != db_task.reminder_time:
        await log_task_event(
            db,
            user_id=user_id,
            task_id=db_task.id,
            event_type=TaskEventType.RESCHEDULED,
            metadata={
                "old_reminder_time": old_reminder_time.isoformat() if old_reminder_time else None,
                "new_reminder_time": db_task.reminder_time.isoformat() if db_task.reminder_time else None,
            },
        )
    await db.commit()
    await db.refresh(db_task)
    return db_task

async def delete_task(db: AsyncSession, task_id: uuid.UUID, user_id: uuid.UUID):
    db_task = await get_task_by_id(db, task_id, user_id)
    if not db_task:
        return None
    
    if db_task.series_id is not None:
        db_task.is_deleted = True
        db_task.deleted_at = datetime.now(timezone.utc)
        db_task.status = StatusEnum.cancelled
        await log_task_event(
            db,
            user_id=user_id,
            task_id=db_task.id,
            event_type=TaskEventType.CANCELLED,
            metadata={"series_id": str(db_task.series_id), "hard_deleted": False},
        )
    else:
        await db.delete(db_task)
        await db.flush()
        await log_task_event(
            db,
            user_id=user_id,
            event_type=TaskEventType.CANCELLED,
            metadata={"deleted_task_id": str(task_id), "hard_deleted": True},
        )
    await db.commit()
    return db_task


async def snooze_task(
    db: AsyncSession,
    task_id: uuid.UUID,
    user_id: uuid.UUID,
    snoozed_until: datetime | None = None,
):
    db_task = await get_task_by_id(db, task_id, user_id)
    if not db_task:
        return None

    db_task.reminder_time = _utc(snoozed_until) if snoozed_until else datetime.now(timezone.utc) + timedelta(minutes=10)
    db_task.is_reminder_sent = False

    await log_task_event(
        db,
        user_id=user_id,
        task_id=db_task.id,
        event_type=TaskEventType.NOT_NOW,
        metadata={"reminder_time": db_task.reminder_time.isoformat()},
    )
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


async def record_overdue_task_events(
    db: AsyncSession,
    occurred_before: datetime | None = None,
) -> int:
    """Record each pending task's overdue transition once per due date."""
    cutoff = occurred_before or datetime.now(timezone.utc)
    result = await db.execute(
        select(Task).where(
            Task.is_deleted.is_(False),
            Task.status.in_([StatusEnum.pending, StatusEnum.in_progress]),
            Task.due_date.is_not(None),
            Task.due_date < cutoff,
        )
    )
    overdue_tasks = result.scalars().all()
    task_ids = [task.id for task in overdue_tasks]
    already_recorded: set[tuple[uuid.UUID, str]] = set()
    for event_model in (TaskEvent, TaskEventOutbox):
        for start in range(0, len(task_ids), 1000):
            result = await db.execute(
                select(event_model.task_id, event_model.event_metadata["due_date"].astext).where(
                    event_model.task_id.in_(task_ids[start : start + 1000]),
                    event_model.event_type == TaskEventType.OVERDUE.value,
                )
            )
            already_recorded.update((task_id, due_date) for task_id, due_date in result.all())

    logged = 0
    for task in overdue_tasks:
        normalized_due_date = _utc(task.due_date)
        if normalized_due_date is None:
            continue
        due_date = normalized_due_date.isoformat()
        if (task.id, due_date) in already_recorded:
            continue
        await log_task_event(
            db,
            user_id=task.user_id,
            task_id=task.id,
            event_type=TaskEventType.OVERDUE,
            metadata={"due_date": due_date},
        )
        logged += 1
    await db.commit()
    return logged

async def get_due_reminders(db: AsyncSession):
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Task)
        .options(selectinload(Task.user))
        .where(
            Task.reminder_time <= now,
            Task.is_reminder_sent == False,
            Task.is_deleted.is_(False),
            Task.status.in_([StatusEnum.pending, StatusEnum.in_progress]),
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
            Task.recurrence.in_(["daily", "weekly", "monthly"]),
            Task.series_id.is_(None),
            Task.recurrence_processed == False,
        )
        .with_for_update(skip_locked=True)
    )
    return result.scalars().all()


async def mark_task_completed(db: AsyncSession, task_id: uuid.UUID, user_id: uuid.UUID):
    task = await get_task_by_id(db, task_id, user_id)
    if not task:
        return None
    was_completed = task.status == StatusEnum.completed
    task.status = StatusEnum.completed
    task.completed_at = datetime.now(timezone.utc)
    if not was_completed:
        await log_task_event(
            db,
            user_id=user_id,
            task_id=task.id,
            event_type=TaskEventType.COMPLETED,
        )
    await db.commit()
    await db.refresh(task)
    return task

async def reschedule_task(db: AsyncSession, task_id, user_id, due_date, reminder_time) -> Task | None:
    task = await get_task_by_id(db, task_id, user_id)
    if not task:
        return None
    old_due_date = task.due_date
    old_reminder_time = task.reminder_time
    if due_date is not None:
        task.due_date = _utc(due_date)
    if reminder_time is not None:
        task.reminder_time = _utc(reminder_time)
        task.is_reminder_sent = False  # new time needs its own reminder fire
    await log_task_event(
        db,
        user_id=user_id,
        task_id=task.id,
        event_type=TaskEventType.RESCHEDULED,
        metadata={
            "old_due": old_due_date.isoformat() if old_due_date else None,
            "new_due": task.due_date.isoformat() if task.due_date else None,
            "old_reminder_time": old_reminder_time.isoformat() if old_reminder_time else None,
            "new_reminder_time": task.reminder_time.isoformat() if task.reminder_time else None,
        },
    )
    if old_due_date != task.due_date:
        await log_task_event(
            db,
            user_id=user_id,
            task_id=task.id,
            event_type=TaskEventType.DEADLINE_CHANGED,
            metadata={
                "old_due": old_due_date.isoformat() if old_due_date else None,
                "new_due": task.due_date.isoformat() if task.due_date else None,
            },
        )
    await db.commit()
    await db.refresh(task)
    return task

async def cancel_task(db: AsyncSession, task_id, user_id) -> Task | None:
    task = await get_task_by_id(db, task_id, user_id)
    if not task:
        return None
    was_deleted = task.is_deleted
    task.is_deleted = True
    task.deleted_at = datetime.now(timezone.utc)
    if not was_deleted:
        await log_task_event(
            db,
            user_id=user_id,
            task_id=task.id,
            event_type=TaskEventType.CANCELLED,
        )
    await db.commit()
    await db.refresh(task)
    return task
