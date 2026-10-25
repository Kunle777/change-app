import logging
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.retrieval import sanitize_for_prompt
from app.tasks.models import StatusEnum, Task, TaskEvent, TaskEventOutbox

OPEN_STATUSES = (StatusEnum.pending, StatusEnum.in_progress)
OPEN_LIMIT = 20
OVERDUE_LIMIT = 15
UPCOMING_DAYS = 7
UPCOMING_LIMIT = 15
COMPLETED_DAYS = 14
COMPLETED_LIMIT = 10
EVENT_DAYS = 30
EVENT_LIMIT = 20
EVENT_TYPES = (
    "not_now",
    "rescheduled",
    "cancelled",
    "deadline_changed",
    "completed",
    "overdue",
)
MAX_TASK_CONTEXT_CHARS = 3500
logger = logging.getLogger(__name__)


@dataclass
class TaskFacts:
    state: str
    prompt: str
    open_count: int = 0
    overdue_count: int = 0
    event_count: int = 0
    queried: bool = False


def _zone(name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(name or "Africa/Lagos")
    except Exception:
        return ZoneInfo("Africa/Lagos")


def _start_of_local_day(zone: ZoneInfo, now: datetime | None = None) -> datetime:
    local = (now or datetime.now(timezone.utc)).astimezone(zone)
    return datetime.combine(local.date(), time.min, tzinfo=zone).astimezone(timezone.utc)


def _fmt_dt(value: datetime | None, zone: ZoneInfo) -> str:
    if value is None:
        return "not set"
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(zone).strftime("%Y-%m-%d %H:%M")


def _status_name(task: Task) -> str:
    status = task.status
    return status.name if hasattr(status, "name") else str(status)


def _priority_name(task: Task) -> str:
    priority = task.priority
    return priority.name if hasattr(priority, "name") else str(priority)


def _task_line(task: Task, zone: ZoneInfo, extra: str = "") -> str:
    title = sanitize_for_prompt(task.title or "", 120)
    description = sanitize_for_prompt(task.description or "", 160)
    due = _fmt_dt(task.due_date, zone)
    pieces = [
        f'- id: {task.id}; title: "{title}"; status: {_status_name(task)}; '
        f"priority: {_priority_name(task)}; due: {due}"
    ]
    if extra:
        pieces.append(extra)
    if description:
        pieces.append(f'description: "{description}"')
    return "; ".join(pieces)


async def _tasks_where(db: AsyncSession, statement) -> list[Task]:
    result = await db.execute(statement)
    return list(result.scalars().all())


async def load_task_facts(
    db: AsyncSession,
    user_id: UUID,
    *,
    need_tasks: bool,
    need_events: bool,
    timezone_name: str | None = None,
    now: datetime | None = None,
) -> TaskFacts:
    if not need_tasks and not need_events:
        return TaskFacts("not_needed", "")

    now = now or datetime.now(timezone.utc)
    zone = _zone(timezone_name)
    today_start = _start_of_local_day(zone, now)
    lines: list[str] = []
    open_count = overdue_count = event_count = 0

    try:
        if need_tasks:
            open_tasks = await _tasks_where(
                db,
                select(Task)
                .where(
                    Task.user_id == user_id,
                    Task.is_deleted.is_(False),
                    Task.status.in_(OPEN_STATUSES),
                )
                .order_by(Task.due_date.asc().nulls_last(), Task.created_at.desc())
                .limit(OPEN_LIMIT),
            )
            overdue = [
                task
                for task in open_tasks
                if task.due_date is not None and task.due_date < today_start
            ][:OVERDUE_LIMIT]
            upcoming_end = today_start + timedelta(days=UPCOMING_DAYS)
            upcoming = [
                task
                for task in open_tasks
                if task.due_date is not None and today_start <= task.due_date < upcoming_end
            ][:UPCOMING_LIMIT]
            undated = [task for task in open_tasks if task.due_date is None][:10]
            completed = await _tasks_where(
                db,
                select(Task)
                .where(
                    Task.user_id == user_id,
                    Task.is_deleted.is_(False),
                    Task.status == StatusEnum.completed,
                    Task.completed_at.is_not(None),
                    Task.completed_at >= now - timedelta(days=COMPLETED_DAYS),
                )
                .order_by(Task.completed_at.desc())
                .limit(COMPLETED_LIMIT),
            )
            cancelled = await _tasks_where(
                db,
                select(Task)
                .where(
                    Task.user_id == user_id,
                    or_(Task.status == StatusEnum.cancelled, Task.is_deleted.is_(True)),
                    Task.deleted_at.is_not(None),
                    Task.deleted_at >= now - timedelta(days=EVENT_DAYS),
                )
                .order_by(Task.deleted_at.desc())
                .limit(8),
            )

            open_count = len(open_tasks)
            overdue_count = len(overdue)
            if overdue:
                lines.append("Overdue open tasks:")
                lines.extend(_task_line(task, zone, "overdue: yes") for task in overdue)
            if upcoming:
                lines.append("Upcoming open tasks (next 7 local days):")
                lines.extend(_task_line(task, zone) for task in upcoming)
            remaining_open = [
                task
                for task in open_tasks
                if task not in overdue and task not in upcoming and task not in undated
            ]
            if remaining_open or (open_tasks and not overdue and not upcoming and not undated):
                shown = remaining_open or open_tasks
                lines.append("Other open tasks:")
                lines.extend(_task_line(task, zone) for task in shown)
            if undated:
                lines.append("Open tasks with no due date:")
                lines.extend(_task_line(task, zone) for task in undated)
            if completed:
                lines.append(f"Completed in the last {COMPLETED_DAYS} days:")
                lines.extend(
                    _task_line(
                        task,
                        zone,
                        extra=f"completed_at: {_fmt_dt(task.completed_at, zone)}",
                    )
                    for task in completed
                )
            if cancelled:
                lines.append("Recently cancelled tasks:")
                lines.extend(_task_line(task, zone) for task in cancelled)
            if not open_tasks and not completed and not cancelled:
                lines.append("The user has no matching tasks in the current window.")

        if need_events:
            since = now - timedelta(days=EVENT_DAYS)
            event_query = union_all(
                select(
                    TaskEvent.id.label("id"),
                    TaskEvent.task_id.label("task_id"),
                    TaskEvent.event_type.label("event_type"),
                    TaskEvent.occurred_at.label("occurred_at"),
                    TaskEvent.event_metadata.label("event_metadata"),
                ).where(
                    TaskEvent.user_id == user_id,
                    TaskEvent.occurred_at >= since,
                    TaskEvent.event_type.in_(EVENT_TYPES),
                ),
                select(
                    TaskEventOutbox.id.label("id"),
                    TaskEventOutbox.task_id.label("task_id"),
                    TaskEventOutbox.event_type.label("event_type"),
                    TaskEventOutbox.occurred_at.label("occurred_at"),
                    TaskEventOutbox.event_metadata.label("event_metadata"),
                ).where(
                    TaskEventOutbox.user_id == user_id,
                    TaskEventOutbox.occurred_at >= since,
                    TaskEventOutbox.event_type.in_(EVENT_TYPES),
                ),
            ).subquery("coaching_task_events")
            rows = (
                await db.execute(
                    select(event_query)
                    .order_by(event_query.c.occurred_at.desc())
                    .limit(EVENT_LIMIT)
                )
            ).all()
            titles = {}
            task_ids = {row.task_id for row in rows if row.task_id}
            if task_ids:
                title_rows = (
                    await db.execute(
                        select(Task.id, Task.title).where(
                            Task.user_id == user_id,
                            Task.id.in_(task_ids),
                        )
                    )
                ).all()
                titles = {row.id: sanitize_for_prompt(row.title or "", 80) for row in title_rows}

            seen = set()
            event_lines = []
            for row in rows:
                if row.id in seen:
                    continue
                seen.add(row.id)
                title = titles.get(row.task_id, "unknown task")
                occurred = _fmt_dt(row.occurred_at, zone)
                meta = row.event_metadata or {}
                extra = ""
                if row.event_type in {"rescheduled", "deadline_changed"}:
                    extra = (
                        f"; old_due={meta.get('old_due')}; new_due={meta.get('new_due')}"
                    )
                event_lines.append(
                    f"- {occurred}: {row.event_type} on \"{title}\"{extra}"
                )
            event_count = len(event_lines)
            if event_lines:
                lines.append(
                    "Recorded task events (only logged actions; incomplete work is not a postponement):"
                )
                lines.extend(event_lines)
            else:
                lines.append(
                    "No recorded postponement, reschedule, cancellation, or completion events "
                    f"in the last {EVENT_DAYS} days."
                )

        prompt = "\n".join(lines)
        if len(prompt) > MAX_TASK_CONTEXT_CHARS:
            prompt = prompt[: MAX_TASK_CONTEXT_CHARS - 1].rstrip() + "…"
        state = "found" if prompt and "no matching tasks" not in prompt.lower() else "none_found"
        if need_tasks and open_count:
            state = "found"
        if need_events and event_count:
            state = "found"
        return TaskFacts(state, prompt, open_count, overdue_count, event_count, queried=True)
    except Exception:
        logger.warning("Structured task context failed", exc_info=True)
        return TaskFacts("unavailable", "", queried=True)
