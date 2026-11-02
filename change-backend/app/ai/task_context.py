import logging
import re
from difflib import SequenceMatcher
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.retrieval import sanitize_for_prompt
from app.ai.safe_text import redact_internal_identifiers
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
_HISTORICAL_QUERY = re.compile(
    r"\b(overdue|history|historical|what happened|what did i|did i have|"
    r"was i|was there|working on)\b",
    re.I,
)
_HISTORICAL_DATE = re.compile(
    r"\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|"
    r"dec(?:ember)?)\s+\d{1,2}(?:st|nd|rd|th)?\b|\b\d{4}-\d{2}-\d{2}\b|"
    r"\b(last|past)\s+(week|month|year)\b|\byesterday\b",
    re.I,
)
_HISTORY_STOP_WORDS = frozenset(
    "what did have was there possible overdue task tasks relating related to on "
    "write wrote about "
    "march january february april may june july august september october november "
    "december jan feb mar apr jun jul aug sep oct nov dec last past week month "
    "year yesterday history historical working with from".split()
)
logger = logging.getLogger(__name__)


@dataclass
class TaskGroup:
    """One headed list of facts. Items are ordered most-important-first so a
    budget can drop from the tail without cutting a line in half."""

    name: str
    priority: float  # lower = kept longest when the context budget is tight
    header: str
    items: list[str]
    min_items: int = 0


def render_groups(groups: list["TaskGroup"], counts: dict[str, int] | None = None) -> str:
    lines: list[str] = []
    for group in groups:
        if not group.items:  # header-only statement, e.g. "no recorded events"
            lines.append(group.header)
            continue
        n = len(group.items) if counts is None else counts.get(group.name, len(group.items))
        if n <= 0:
            continue
        lines.append(group.header)
        lines.extend(group.items[:n])
    return "\n".join(lines)


@dataclass
class TaskFacts:
    state: str
    prompt: str
    open_count: int = 0
    overdue_count: int = 0
    event_count: int = 0
    queried: bool = False
    groups: list[TaskGroup] = field(default_factory=list)


def _zone(name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(name or "Africa/Lagos")
    except Exception:
        return ZoneInfo("Africa/Lagos")


def _start_of_local_day(zone: ZoneInfo, now: datetime | None = None) -> datetime:
    local = (now or datetime.now(timezone.utc)).astimezone(zone)
    return datetime.combine(local.date(), time.min, tzinfo=zone).astimezone(timezone.utc)


def _is_overdue(task: Task, now: datetime, today_start: datetime) -> bool:
    if task.due_date is None:
        return False
    due_date = _fmt_aware(task.due_date)
    if getattr(task, "due_date_is_all_day", None) is None:
        return due_date < today_start
    return due_date < now


def _fmt_aware(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


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
    title = redact_internal_identifiers(sanitize_for_prompt(task.title or "", 120))
    description = redact_internal_identifiers(
        sanitize_for_prompt(task.description or "", 160)
    )
    if task.due_date is None:
        due = "not set"
    elif getattr(task, "due_date_is_all_day", None) is True:
        due = _fmt_dt(task.due_date, zone).split(" ", 1)[0] + " (date only)"
    elif getattr(task, "due_date_is_all_day", None) is None:
        due = (
            _fmt_dt(task.due_date, zone).split(" ", 1)[0]
            + " (time unspecified; legacy deadline type unknown)"
        )
    else:
        due = _fmt_dt(task.due_date, zone)
    reminder = _fmt_dt(getattr(task, "reminder_time", None), zone)
    pieces = [
        f'- title: "{title}"; status: {_status_name(task)}; '
        f"priority: {_priority_name(task)}; deadline: {due}; reminder: {reminder}"
    ]
    if extra:
        pieces.append(extra)
    if description:
        pieces.append(f'description: "{description}"')
    return "; ".join(pieces)


def _normalized_title(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", (value or "").casefold()))


def is_historical_task_question(message: str) -> bool:
    return bool(_HISTORICAL_QUERY.search(message or "") and _HISTORICAL_DATE.search(message or ""))


async def load_task_history_facts(
    db: AsyncSession,
    user_id: UUID,
    message: str,
    timezone_name: str | None = None,
) -> TaskFacts:
    terms = [
        word for word in re.findall(r"[a-z0-9]+", (message or "").casefold())
        if (
            len(word) >= 3
            and word not in _HISTORY_STOP_WORDS
            and not word.isdigit()
            and not re.fullmatch(r"\d+(?:st|nd|rd|th)", word)
        )
    ]
    terms = list(dict.fromkeys(terms))
    if not terms:
        return TaskFacts(
            "none_found",
            "Historical task search had no task-title terms to search.",
        )

    try:
        statement = (
            select(Task)
            .where(
                Task.user_id == user_id,
                or_(*(Task.title.ilike(f"%{term}%") for term in terms)),
            )
            .order_by(Task.created_at.desc())
            .limit(50)
        )
        matches = await _tasks_where(db, statement)
    except Exception:
        logger.warning("Historical task search failed", exc_info=True)
        return TaskFacts(
            "unavailable",
            "Historical task records could not be retrieved because of a technical issue. "
            "Do not claim that no matching task exists.",
        )

    if not matches:
        return TaskFacts(
            "none_found",
            "Historical task search found no available task records matching the "
            "title terms. This search includes open, completed, cancelled, undated, "
            "and soft-deleted task records.",
        )

    zone = _zone(timezone_name)
    items = [
        _task_line(
            task,
            zone,
            extra=(
                f"completed_at: {_fmt_dt(task.completed_at, zone)}"
                if task.completed_at
                else f"deleted_at: {_fmt_dt(task.deleted_at, zone)}"
                if task.deleted_at
                else ""
            ),
        )
        for task in matches
    ]
    group = TaskGroup(
        "historical_tasks",
        0.05,
        f"Historical task search matched {len(matches)} available record(s) across task statuses:",
        items,
        min_items=min(len(items), 5),
    )
    return TaskFacts("found", render_groups([group]), groups=[group])


async def find_tasks_by_name(
    db: AsyncSession,
    user_id: UUID,
    name: str,
    *,
    open_only: bool = False,
    for_update: bool = False,
) -> list[Task]:
    """Search the owner's full task history and rank exact, partial, and typo matches."""
    query = _normalized_title(name)
    if len(query) < 3:
        return []
    statement = select(Task).where(Task.user_id == user_id)
    if open_only:
        statement = statement.where(
            Task.is_deleted.is_(False), Task.status.in_(OPEN_STATUSES)
        )
    if for_update:
        statement = statement.with_for_update().execution_options(populate_existing=True)
    tasks = (await db.execute(statement)).scalars().all()
    ranked: list[tuple[float, Task]] = []
    for task in tasks:
        title = _normalized_title(task.title or "")
        if not title:
            continue
        if title == query:
            score = 1.0
        elif query in title or title in query:
            score = 0.9 + 0.1 * min(len(query), len(title)) / max(len(query), len(title))
        else:
            score = SequenceMatcher(None, query, title).ratio()
        if score >= 0.68:
            ranked.append((score, task))
    ranked.sort(
        key=lambda item: (
            -item[0],
            (item[1].created_at.isoformat() if item[1].created_at else ""),
        )
    )
    if not ranked:
        return []
    best = ranked[0][0]
    return [task for score, task in ranked if score >= max(0.68, best - 0.12)]


async def _tasks_where(db: AsyncSession, statement) -> list[Task]:
    result = await db.execute(statement)
    return list(result.scalars().all())


async def load_open_task_titles(db: AsyncSession, user_id: UUID, limit: int = 50) -> list[str]:
    """Titles of the user's own open tasks, used only to detect that a message names one."""
    try:
        result = await db.execute(
            select(Task.title)
            .where(
                Task.user_id == user_id,
                Task.is_deleted.is_(False),
                Task.status.in_(OPEN_STATUSES),
            )
            .order_by(Task.due_date.asc().nulls_last(), Task.created_at.desc())
            .limit(limit)
        )
        return [title for title in result.scalars().all() if title]
    except Exception:
        logger.warning("Could not load open task titles", exc_info=True)
        return []


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
    groups: list[TaskGroup] = []
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
                task for task in open_tasks if _is_overdue(task, now, today_start)
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
                groups.append(TaskGroup(
                    "overdue", 0.0,
                    "Overdue open tasks (they remain in the task list and are not "
                    "automatically moved to today):",
                    [_task_line(task, zone, "overdue: yes") for task in overdue], min_items=3,
                ))
            if upcoming:
                groups.append(TaskGroup(
                    "upcoming", 0.1, "Upcoming open tasks (next 7 local days):",
                    [_task_line(task, zone) for task in upcoming], min_items=3,
                ))
            remaining_open = [
                task
                for task in open_tasks
                if task not in overdue and task not in upcoming and task not in undated
            ]
            if remaining_open or (open_tasks and not overdue and not upcoming and not undated):
                shown = remaining_open or open_tasks
                groups.append(TaskGroup(
                    "other_open", 0.2, "Other open tasks:",
                    [_task_line(task, zone) for task in shown], min_items=2,
                ))
            if undated:
                groups.append(TaskGroup(
                    "undated", 0.3, "Open tasks with no due date:",
                    [_task_line(task, zone) for task in undated], min_items=2,
                ))
            if completed:
                groups.append(TaskGroup(
                    "completed", 5.0, f"Completed in the last {COMPLETED_DAYS} days:",
                    [
                        _task_line(
                            task, zone, extra=f"completed_at: {_fmt_dt(task.completed_at, zone)}"
                        )
                        for task in completed
                    ],
                ))
            if cancelled:
                groups.append(TaskGroup(
                    "cancelled", 6.0, "Recently cancelled tasks:",
                    [_task_line(task, zone) for task in cancelled],
                ))
            if not open_tasks and not completed and not cancelled:
                groups.append(TaskGroup(
                    "no_tasks", 0.0, "The user has no matching tasks in the current window.", [],
                ))

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
                titles = {
                    row.id: redact_internal_identifiers(
                        sanitize_for_prompt(row.title or "", 80)
                    )
                    for row in title_rows
                }

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
                    old_due = redact_internal_identifiers(str(meta.get("old_due") or "not set"))
                    new_due = redact_internal_identifiers(str(meta.get("new_due") or "not set"))
                    extra = f"; old_due={old_due}; new_due={new_due}"
                event_lines.append(
                    f"- {occurred}: {row.event_type} on \"{title}\"{extra}"
                )
            event_count = len(event_lines)
            if event_lines:
                groups.append(TaskGroup(
                    "events", 3.0,
                    "Recorded task events (only logged actions; incomplete work is not a postponement):",
                    event_lines,
                ))
            else:
                groups.append(TaskGroup(
                    "events_none", 3.0,
                    "No recorded postponement, reschedule, cancellation, or completion events "
                    f"in the last {EVENT_DAYS} days.",
                    [],
                ))

        # No truncation here: the global context budget trims whole items by priority.
        prompt = render_groups(groups)
        state = "found" if prompt and "no matching tasks" not in prompt.lower() else "none_found"
        if need_tasks and open_count:
            state = "found"
        if need_events and event_count:
            state = "found"
        return TaskFacts(
            state, prompt, open_count, overdue_count, event_count, queried=True, groups=groups
        )
    except Exception:
        logger.warning("Structured task context failed", exc_info=True)
        return TaskFacts("unavailable", "", queried=True)
