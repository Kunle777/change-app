import uuid
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from app.ai.prompt_builder import build_system_prompt_for_user
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
from app.users.models import User


def _local_day_start_utc(timezone_name: str | None, target_date: date | None = None) -> datetime:
    zone = ZoneInfo(timezone_name or "Africa/Lagos")
    local_date = target_date or datetime.now(zone).date()
    return datetime.combine(local_date, time.min, tzinfo=zone).astimezone(timezone.utc)


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

async def create_task(
    db: AsyncSession,
    task_data: TaskCreate,
    user_id: uuid.UUID,
    *,
    commit: bool = True,
):
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
        priority_reminder=task_data.priority_reminder,
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
    if commit:
        await db.commit()
        await db.refresh(db_task)
    else:
        await db.flush()
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


async def get_undated_tasks(db: AsyncSession, user_id: uuid.UUID):
    result = await db.execute(
        select(Task)
        .where(
            Task.user_id == user_id,
            Task.is_deleted.is_(False),
            Task.status == StatusEnum.pending,
            Task.due_date.is_(None),
        )
        .order_by(Task.created_at.desc())
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

async def get_task_by_id(
    db: AsyncSession,
    task_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    for_update: bool = False,
):
    query = select(Task).where(
        Task.id == task_id,
        Task.user_id == user_id,
        Task.is_deleted.is_(False),
    )
    if for_update:
        query = query.with_for_update().execution_options(populate_existing=True)
    result = await db.execute(query)
    return result.scalar_one_or_none()
    
async def update_task(
    db: AsyncSession,
    task_id: uuid.UUID,
    task_data: TaskUpdate,
    user_id: uuid.UUID,
    *,
    commit: bool = True,
):
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
    if commit:
        await db.commit()
        await db.refresh(db_task)
    else:
        await db.flush()
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


def _end_of_local_day_utc(local_date: date, timezone_name: str | None) -> datetime:
    """Return 23:59:59.999000 of local_date stored as UTC (matches frontend convention)."""
    zone = ZoneInfo(timezone_name or "Africa/Lagos")
    end_local = datetime(
        local_date.year, local_date.month, local_date.day,
        23, 59, 59, 999000, tzinfo=zone,
    )
    return end_local.astimezone(timezone.utc)


async def snooze_task(
    db: AsyncSession,
    task_id: uuid.UUID,
    user_id: uuid.UUID,
    snoozed_until: datetime | None = None,
):
    db_task = await get_task_by_id(db, task_id, user_id)
    if not db_task:
        return None

    tz_result = await db.execute(select(User.last_active_timezone).where(User.id == user_id))
    tz_name: str | None = tz_result.scalar_one_or_none()

    new_reminder = _utc(snoozed_until) if snoozed_until else datetime.now(timezone.utc) + timedelta(minutes=10)
    db_task.reminder_time = new_reminder
    db_task.is_reminder_sent = False

    # Move due_date forward when the reminder crosses into a later calendar day.
    old_due = db_task.due_date
    if old_due is not None:
        zone = ZoneInfo(tz_name or "Africa/Lagos")
        reminder_local_date = new_reminder.astimezone(zone).date()
        due_local_date = old_due.astimezone(zone).date()
        if reminder_local_date > due_local_date:
            new_due = _end_of_local_day_utc(reminder_local_date, tz_name)
            db_task.due_date = new_due
            await log_task_event(
                db,
                user_id=user_id,
                task_id=db_task.id,
                event_type=TaskEventType.DEADLINE_CHANGED,
                metadata={
                    "old_due": old_due.isoformat(),
                    "new_due": new_due.isoformat(),
                    "reason": "not_now",
                },
            )

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


async def get_overdue_tasks(
    db: AsyncSession,
    user_id: uuid.UUID,
    timezone_name: str | None = None,
    limit: int = 20,
) -> dict:
    start_of_today = _local_day_start_utc(timezone_name)
    base_filter = and_(
        Task.user_id == user_id,
        Task.due_date < start_of_today,
        Task.status.in_([StatusEnum.pending, StatusEnum.in_progress]),
        Task.is_deleted.is_(False),
    )
    count_result = await db.execute(select(func.count()).select_from(Task).where(base_filter))
    total: int = count_result.scalar_one()
    tasks_result = await db.execute(
        select(Task).where(base_filter).order_by(Task.due_date.asc()).limit(limit)
    )
    return {"count": total, "tasks": tasks_result.scalars().all()}


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

    context = (
        f"Task title: {task.title}\n"
        f"Task description: {task.description or 'No description provided'}"
    )
    prompt, _ = await build_system_prompt_for_user(
        db,
        user_id,
        "task_help",
        context,
        additional_instructions=(
            "Break the supplied task into 3-6 small, concrete, actionable steps. "
            "Respond with only a JSON array of strings, each string one step. "
            "Do not include extra text or markdown formatting."
        ),
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

async def cancel_task(
    db: AsyncSession,
    task_id,
    user_id,
    *,
    commit: bool = True,
) -> Task | None:
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
    if commit:
        await db.commit()
        await db.refresh(task)
    else:
        await db.flush()
    return task


async def get_task_dates_for_month(
    db: AsyncSession, user_id, year: int, month: int, timezone_name: str | None = None
) -> list[str]:
    start_day = date(year, month, 1)
    end_day = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    start = _local_day_start_utc(timezone_name, start_day)
    end = _local_day_start_utc(timezone_name, end_day)
    result = await db.execute(
        select(Task.due_date).where(
            Task.user_id == user_id,
            Task.is_deleted.is_(False),
            Task.due_date >= start,
            Task.due_date < end,
        )
    )
    zone = ZoneInfo(timezone_name or "Africa/Lagos")
    return sorted({_utc(d).astimezone(zone).date().isoformat() for d in result.scalars().all() if d})


async def get_tasks_for_date(
    db: AsyncSession,
    user_id,
    target_date: date,
    status_filter: str = "all",
    timezone_name: str | None = None,
) -> list[Task]:
    zone = ZoneInfo(timezone_name or "Africa/Lagos")
    local_today = datetime.now(zone).date()
    if status_filter == "overdue" and target_date >= local_today:
        return []
    start = _local_day_start_utc(timezone_name, target_date)
    end = _local_day_start_utc(timezone_name, target_date + timedelta(days=1))
    query = select(Task).where(
        Task.user_id == user_id,
        Task.is_deleted.is_(False),
        Task.due_date >= start,
        Task.due_date < end,
    )
    if status_filter == "incomplete":
        query = query.where(Task.status.in_([StatusEnum.pending, StatusEnum.in_progress]))
    elif status_filter == "completed":
        query = query.where(Task.status == StatusEnum.completed)
    elif status_filter == "overdue":
        query = query.where(
            Task.status.in_([StatusEnum.pending, StatusEnum.in_progress]),
            Task.due_date < _local_day_start_utc(timezone_name),
        )
    query = query.order_by(Task.status, Task.reminder_time)
    result = await db.execute(query)
    return result.scalars().all()
