from calendar import monthrange
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.tasks.models import (
    PriorityEnum,
    StatusEnum,
    Task,
    TaskEventType,
    TaskSeries,
)
from app.tasks.task_event_service import log_task_event


def _occurrence_dates(series: TaskSeries, first_date: date, last_date: date):
    start = series.start_date
    every = max(1, series.interval)
    if series.frequency == "daily":
        periods = max(0, (first_date - start).days // every)
        candidate = start + timedelta(days=periods * every)
        while candidate < first_date:
            candidate += timedelta(days=every)
        advance = lambda value: value + timedelta(days=every)
    elif series.frequency == "weekly":
        week_days = 7 * every
        selected_days = set(series.days_of_week or [start.weekday()])
        week_anchor = start - timedelta(days=start.weekday())
        cursor = max(start, first_date)
        while cursor.weekday() not in selected_days:
            cursor += timedelta(days=1)
        def weekly_dates():
            current = cursor
            while current <= last_date:
                elapsed_weeks = ((current - week_anchor).days // 7)
                if elapsed_weeks >= 0 and elapsed_weeks % every == 0:
                    yield current
                current += timedelta(days=1)
        for weekly_date in weekly_dates():
            if series.end_date is not None and weekly_date > series.end_date:
                break
            yield weekly_date
        return
    elif series.frequency == "monthly":
        month_delta = (first_date.year - start.year) * 12 + first_date.month - start.month
        periods = max(0, month_delta // every)
        candidate = start + relativedelta(months=periods * every)
        while candidate < first_date:
            periods += 1
            candidate = start + relativedelta(months=periods * every)
        def advance(value: date) -> date:
            offset = ((value.year - start.year) * 12 + value.month - start.month) // every + 1
            target_month = start + relativedelta(months=offset * every)
            # Keep the original day-of-month when possible, otherwise use month end.
            day = min(start.day, monthrange(target_month.year, target_month.month)[1])
            return target_month.replace(day=day)
    else:
        return

    while candidate <= last_date:
        if series.end_date is not None and candidate > series.end_date:
            break
        yield candidate
        next_date = advance(candidate)
        if next_date <= candidate:
            break
        candidate = next_date


async def generate_recurring_task_occurrences(
    db: AsyncSession,
    *,
    horizon_days: int = 30,
    today: date | None = None,
) -> int:
    """Create missing occurrences inside a bounded window; safe under retried workers."""
    series_result = await db.execute(
        select(TaskSeries)
        .where(TaskSeries.is_active.is_(True))
        .order_by(TaskSeries.created_at)
        .with_for_update(skip_locked=True)
    )
    created_count = 0
    for series in series_result.scalars().all():
        zone = ZoneInfo(series.timezone)
        local_today = today or datetime.now(zone).date()
        last_date = local_today + timedelta(days=horizon_days)
        existing_result = await db.execute(
            select(Task.occurrence_date).where(Task.series_id == series.id)
        )
        existing_dates = set(existing_result.scalars().all())

        for occurrence_date in _occurrence_dates(series, local_today, last_date):
            if occurrence_date in existing_dates:
                continue
            if series.occurrence_limit is not None and series.generated_count >= series.occurrence_limit:
                series.is_active = False
                break

            due_at = datetime.combine(occurrence_date, series.local_time or time.max, tzinfo=zone)
            reminder_at = (
                datetime.combine(occurrence_date, series.local_time, tzinfo=zone)
                if series.local_time is not None
                else None
            )
            task = Task(
                user_id=series.user_id,
                title=series.title,
                description=series.description,
                priority=PriorityEnum[series.priority],
                status=StatusEnum.pending,
                due_date=due_at.astimezone(timezone.utc),
                reminder_time=reminder_at.astimezone(timezone.utc) if reminder_at else None,
                recurrence=series.frequency,
                series_id=series.id,
                occurrence_date=occurrence_date,
            )
            db.add(task)
            await db.flush()
            await log_task_event(
                db,
                user_id=series.user_id,
                task_id=task.id,
                event_type=TaskEventType.CREATED,
                metadata={"series_id": str(series.id), "occurrence_date": occurrence_date.isoformat()},
            )
            existing_dates.add(occurrence_date)
            series.generated_count += 1
            created_count += 1

        if series.occurrence_limit is not None and series.generated_count >= series.occurrence_limit:
            series.is_active = False

    await db.commit()
    return created_count


async def stop_task_series(db: AsyncSession, task_id, user_id) -> bool:
    task_result = await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == user_id)
    )
    task = task_result.scalar_one_or_none()
    if task is None or task.series_id is None:
        return False

    series_result = await db.execute(
        select(TaskSeries)
        .where(TaskSeries.id == task.series_id, TaskSeries.user_id == user_id)
        .with_for_update()
    )
    series = series_result.scalar_one_or_none()
    if series is None:
        return False
    series.is_active = False
    cutoff = datetime.now(ZoneInfo(series.timezone)).date()
    future_result = await db.execute(
        select(Task).where(
            Task.series_id == series.id,
            Task.status == StatusEnum.pending,
            Task.occurrence_date > cutoff,
            Task.is_deleted.is_(False),
        )
    )
    for occurrence in future_result.scalars().all():
        occurrence.status = StatusEnum.cancelled
        occurrence.is_deleted = True
        occurrence.deleted_at = datetime.now(timezone.utc)
        await log_task_event(
            db,
            user_id=user_id,
            task_id=occurrence.id,
            event_type=TaskEventType.CANCELLED,
            metadata={"series_id": str(series.id), "reason": "series_stopped"},
        )
    await db.commit()
    return True
