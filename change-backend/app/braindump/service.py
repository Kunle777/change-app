import asyncio
import json
import re
import uuid
from datetime import datetime
import uuid

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import gemini
from app.braindump.models import BrainDump
from app.braindump.schemas import BrainDumpCreate, ParsedTaskSuggestion, SuggestedRecurrenceRule
from app.tasks.models import PriorityEnum, Task, TaskEventType, TaskSeries
from app.tasks.schemas import TaskCreate
from app.tasks.task_event_service import log_task_event


async def create_brain_dump(db: AsyncSession, brain_dump: BrainDumpCreate, user_id: uuid.UUID):
    db_brain_dump = BrainDump(
        user_id=user_id,
        content=brain_dump.content,
        source=brain_dump.source,
        is_converted=False,
    )
    db.add(db_brain_dump)
    await db.commit()
    await db.refresh(db_brain_dump)
    return db_brain_dump


async def get_brain_dumps_for_user(db: AsyncSession, user_id: uuid.UUID):
    result = await db.execute(select(BrainDump).where(BrainDump.user_id == user_id))
    return result.scalars().all()


async def get_brain_dump_by_id(db: AsyncSession, brain_dump_id: uuid.UUID, user_id: uuid.UUID):
    result = await db.execute(
        select(BrainDump).where(
            and_(BrainDump.id == brain_dump_id, BrainDump.user_id == user_id)
        )
    )
    return result.scalar_one_or_none()


async def delete_brain_dump(db: AsyncSession, brain_dump_id: uuid.UUID, user_id: uuid.UUID):
    brain_dump = await get_brain_dump_by_id(db, brain_dump_id, user_id)
    if not brain_dump:
        return None
    await db.delete(brain_dump)
    await db.commit()
    return brain_dump


PRIORITY_MAP = {
    "low": PriorityEnum.low,
    "medium": PriorityEnum.medium,
    "high": PriorityEnum.high,
}


async def parse_dump(db: AsyncSession, dump_id: uuid.UUID, user_id: uuid.UUID):
    dump = await get_brain_dump_by_id(db, dump_id, user_id)
    if not dump:
        return None

    prompt = (
        "Extract distinct actionable tasks from the note. Return a JSON array; each item "
        'must contain "title" (short, action-oriented) and "priority" '
        '(low, medium, or high). Include "recurrence_rule" only when the note clearly '
        'requests repetition; it must contain frequency (daily, weekly, or monthly), '
        'interval, and optional days_of_week using Monday=0 through Sunday=6. Do not '
        'include reminder times, due dates, or an inferred start date. Return [] if '
        "there are no actionable tasks. Do not invent tasks.\n\nNote:\n" + dump.content
    )
    try:
        raw = await asyncio.to_thread(gemini.generate_response, prompt)
    except Exception as error:
        raise ValueError("AI task parsing is temporarily unavailable") from error
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("AI returned an empty task suggestion response")
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError("AI returned invalid task suggestions") from error
    if not isinstance(parsed, list):
        raise ValueError("AI task suggestions must be a JSON list")

    suggestions: list[ParsedTaskSuggestion] = []
    for item in parsed[:30]:
        if not isinstance(item, dict):
            continue
        title = item.get("title")
        if not isinstance(title, str) or not title.strip():
            continue
        priority = item.get("priority", "medium")
        if not isinstance(priority, str) or priority.lower() not in PRIORITY_MAP:
            priority = "medium"
        recurrence_rule = None
        raw_rule = item.get("recurrence_rule")
        if isinstance(raw_rule, dict):
            try:
                recurrence_rule = SuggestedRecurrenceRule.model_validate(raw_rule)
            except Exception:
                recurrence_rule = None
        suggestions.append(ParsedTaskSuggestion(
            title=title.strip()[:200],
            priority=priority.lower(),
            recurrence_rule=recurrence_rule,
        ))
    return suggestions


async def convert_to_task(
    db: AsyncSession,
    dump_id: uuid.UUID,
    user_id: uuid.UUID,
    suggestions: list[dict],
):
    # Serialize conversions of the same dump so a retry or double tap cannot
    # create duplicate tasks. The row lock is held through the single commit.
    result = await db.execute(
        select(BrainDump)
        .where(BrainDump.id == dump_id, BrainDump.user_id == user_id)
        .with_for_update()
    )
    dump = result.scalar_one_or_none()
    if not dump:
        return None

    if dump.is_converted:
        existing = await db.execute(
            select(Task).where(
                Task.source_brain_dump_id == dump.id,
                Task.user_id == user_id,
            )
        )
        return existing.scalars().all()

    created_tasks: list[Task] = []
    for suggestion in suggestions:
        title = suggestion["title"].strip()
        if not title:
            continue
        priority = PRIORITY_MAP.get(suggestion.get("priority", "medium"), PriorityEnum.medium)
        raw_rule = suggestion.get("recurrence_rule")
        series = None
        due_date = None
        recurrence = None
        if isinstance(raw_rule, dict):
            from zoneinfo import ZoneInfo
            from datetime import time, timezone

            from app.tasks.schemas import TaskRecurrenceCreate

            try:
                timezone_name = raw_rule.get("timezone") or "Africa/Lagos"
                zone = ZoneInfo(timezone_name)
                rule = TaskRecurrenceCreate(
                    frequency=raw_rule["frequency"],
                    interval=raw_rule.get("interval", 1),
                    days_of_week=raw_rule.get("days_of_week", []),
                    start_date=raw_rule.get("start_date") or datetime.now(zone).date(),
                    timezone=timezone_name,
                    end_date=raw_rule.get("end_date"),
                    occurrence_limit=raw_rule.get("occurrence_limit"),
                )
                series = TaskSeries(
                    user_id=user_id,
                    title=title[:200],
                    priority=priority.name,
                    frequency=rule.frequency,
                    interval=rule.interval,
                    days_of_week=rule.days_of_week,
                    start_date=rule.start_date,
                    local_time=None,
                    timezone=rule.timezone,
                    end_date=rule.end_date,
                    occurrence_limit=rule.occurrence_limit,
                    generated_count=1,
                    is_active=rule.occurrence_limit != 1,
                )
                db.add(series)
                await db.flush()
                due_date = datetime.combine(series.start_date, time.max, tzinfo=zone).astimezone(timezone.utc)
                recurrence = series.frequency
            except (KeyError, TypeError, ValueError):
                series = None
                recurrence = None
                due_date = None
        task_data = TaskCreate(title=title[:200], priority=priority)
        task = Task(
            user_id=user_id,
            title=task_data.title,
            priority=task_data.priority,
            status=task_data.status,
            description=task_data.description,
            due_date=due_date or task_data.due_date,
            reminder_time=task_data.reminder_time,
            recurrence=recurrence or (task_data.recurrence.name if task_data.recurrence else None),
            series_id=series.id if series else None,
            occurrence_date=series.start_date if series else None,
            source_brain_dump_id=dump.id,
        )
        db.add(task)
        created_tasks.append(task)

    dump.is_converted = True
    try:
        await db.flush()
        dump.created_task_id = created_tasks[0].id if created_tasks else None
        for task in created_tasks:
            await log_task_event(
                db,
                user_id=user_id,
                task_id=task.id,
                event_type=TaskEventType.CREATED,
                metadata={"source": "brain_dump", "brain_dump_id": str(dump.id)},
            )
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    for task in created_tasks:
        await db.refresh(task)
    return created_tasks
