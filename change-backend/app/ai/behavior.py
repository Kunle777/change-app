import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import and_, or_, select, union
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.retrieval import sanitize_for_prompt
from app.checkins.models import CheckIn
from app.tasks.models import StatusEnum, Task, TaskEvent, TaskEventOutbox

WINDOW_DAYS = 30
MIN_POSTPONES = 3
MIN_DEADLINE_MOVES = 2
MIN_COMPLETIONS_FOR_RATE = 5
MAX_OBSERVATIONS = 6
MAX_CHARS = 1200
MAX_CHECKINS_IN_PROMPT = 10
OVERWHELM_CUES = re.compile(r"\b(overwhelmed|overwhelm|too much|stressed|can't cope|cannot cope)\b", re.I)
logger = logging.getLogger(__name__)


@dataclass
class Observation:
    text: str
    subject: str = ""  # task title the observation is about; "" for general counts


BEHAVIOR_GUIDANCE = (
    "How to use these: they are background, not a script. Mention at most ONE, and only "
    "if it genuinely helps with what the user asked. Do not recite counts or numbers "
    "unless they ask for them. Prefer a gentle offer ('want to make that one smaller?') "
    "to a statement about them. Never explain WHY they do anything, and never infer "
    "traits, motivation, or any psychological or medical condition from task activity; "
    "postponing can have many ordinary reasons."
)


def render_observations(observations: list["Observation"]) -> str:
    if not observations:
        return ""
    body = "\n".join(f"- {item.text}" for item in observations[:MAX_OBSERVATIONS])
    prompt = (
        "Behavioral observations (derived from recorded task events only; "
        "these are observations, not diagnoses or character labels):\n"
        f"{body}\n{BEHAVIOR_GUIDANCE}"
    )
    return prompt


def drop_recently_mentioned(
    observations: list["Observation"], recent_replies: list[str]
) -> list["Observation"]:
    """Skip observations about a task the coach already brought up in its last replies."""
    recent = " ".join(recent_replies).lower()
    return [
        item
        for item in observations
        if not (item.subject and item.subject.lower() in recent)
    ]


@dataclass
class BehaviorFacts:
    state: str
    prompt: str
    observation_count: int = 0
    observations: list[Observation] = field(default_factory=list)


def _as_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


async def load_behavior_observations(
    db: AsyncSession,
    user_id: UUID,
    *,
    needed: bool,
    timezone_name: str | None = None,
    now: datetime | None = None,
) -> BehaviorFacts:
    if not needed:
        return BehaviorFacts("not_needed", "")

    now = now or datetime.now(timezone.utc)
    since = now - timedelta(days=WINDOW_DAYS)
    try:
        local_zone = ZoneInfo(timezone_name or "Africa/Lagos")
    except Exception:
        local_zone = ZoneInfo("Africa/Lagos")
    try:
        event_query = union(
            select(
                TaskEvent.task_id,
                TaskEvent.event_type,
                TaskEvent.occurred_at,
                TaskEvent.event_metadata,
            ).where(
                TaskEvent.user_id == user_id,
                TaskEvent.occurred_at >= since,
                TaskEvent.event_type.in_(
                    (
                        "not_now",
                        "rescheduled",
                        "deadline_changed",
                        "completed",
                        "cancelled",
                        "overdue",
                    )
                ),
            ),
            select(
                TaskEventOutbox.task_id,
                TaskEventOutbox.event_type,
                TaskEventOutbox.occurred_at,
                TaskEventOutbox.event_metadata,
            ).where(
                TaskEventOutbox.user_id == user_id,
                TaskEventOutbox.occurred_at >= since,
                TaskEventOutbox.event_type.in_(
                    (
                        "not_now",
                        "rescheduled",
                        "deadline_changed",
                        "completed",
                        "cancelled",
                        "overdue",
                    )
                ),
            ),
        )
        rows = (await db.execute(event_query)).all()
        tasks = (
            await db.execute(
                select(Task).where(
                    Task.user_id == user_id,
                    Task.is_deleted.is_(False),
                    or_(
                        Task.created_at >= since,
                        and_(
                            Task.status == StatusEnum.completed,
                            Task.completed_at >= since,
                        ),
                    ),
                )
            )
        ).scalars().all()
        checkins = (
            await db.execute(
                select(CheckIn)
                .where(
                    CheckIn.user_id == user_id,
                    CheckIn.created_at >= since,
                )
                .order_by(CheckIn.created_at.desc())
                .limit(100)
            )
        ).scalars().all()
        checkins.reverse()
        checkin_state = "found" if checkins else "none_found"
    except Exception:
        logger.warning("Behavioral observations failed", exc_info=True)
        return BehaviorFacts("unavailable", "")

    checkin_lines = ["Check-in history (last 30 days; original recorded data):"]
    if checkin_state == "unavailable":
        checkin_lines.append("Original check-in history could not be retrieved.")
    elif not checkins:
        checkin_lines.append("No check-in records were found in this time window.")
    else:
        for item in checkins[-MAX_CHECKINS_IN_PROMPT:]:
            stamp = _as_aware(item.created_at)
            local_time = (
                stamp.astimezone(local_zone).strftime("%Y-%m-%d %H:%M")
                if stamp
                else "unknown time"
            )
            mood = f"mood {item.mood}/5" if item.mood is not None else "mood not recorded"
            details = [mood]
            for label, value in (("goal", item.goal_today), ("reflection", item.reflection)):
                if value and value.strip():
                    details.append(f'{label}: "{sanitize_for_prompt(value, 180)}"')
            checkin_lines.append(
                f"- {local_time} ({item.type.value}): " + "; ".join(details)
            )

    if not rows and not tasks and not checkins:
        return BehaviorFacts(
            "none_found",
            "Behavioral observations: not enough recorded task events in the last "
            f"{WINDOW_DAYS} days to describe a pattern. Lack of recorded activity "
            "is not evidence that the user did nothing.\n"
            + "\n".join(checkin_lines),
        )

    titles = {}
    title_ids = {row.task_id for row in rows if row.task_id}
    if title_ids:
        title_rows = (
            await db.execute(
                select(Task.id, Task.title).where(
                    Task.user_id == user_id, Task.id.in_(title_ids)
                )
            )
        ).all()
        titles = {row.id: sanitize_for_prompt(row.title or "", 80) for row in title_rows}

    postpones = Counter()
    deadline_moves = Counter()
    cancellations = Counter()
    overdue_transitions = Counter()
    for row in rows:
        if row.task_id is None:
            continue
        if row.event_type == "not_now":
            postpones[row.task_id] += 1
        elif row.event_type in {"deadline_changed", "rescheduled"}:
            deadline_moves[row.task_id] += 1
        elif row.event_type == "cancelled":
            cancellations[row.task_id] += 1
        elif row.event_type == "overdue":
            overdue_transitions[row.task_id] += 1

    observations: list[Observation] = []
    for task_id, count in postpones.most_common():
        if count < MIN_POSTPONES:
            continue
        title = titles.get(task_id, "a task")
        observations.append(Observation(
            f'Observed: "{title}" has {count} recorded postponements ("not now") '
            f"in the last {WINDOW_DAYS} days.",
            title,
        ))
        if len(observations) >= MAX_OBSERVATIONS:
            break

    if len(observations) < MAX_OBSERVATIONS:
        for task_id, count in deadline_moves.most_common():
            if count < MIN_DEADLINE_MOVES:
                continue
            title = titles.get(task_id, "a task")
            observations.append(Observation(
                f'Observed: "{title}" had {count} recorded deadline changes or '
                f"reschedules in the last {WINDOW_DAYS} days.",
                title,
            ))
            if len(observations) >= MAX_OBSERVATIONS:
                break

    if len(observations) < MAX_OBSERVATIONS:
        repeated_overdue = sum(count for count in overdue_transitions.values())
        if repeated_overdue >= MIN_POSTPONES:
            observations.append(Observation(
                f"Observed: {repeated_overdue} overdue transitions were recorded "
                f"across tasks in the last {WINDOW_DAYS} days. This count does not "
                "establish why deadlines were missed."
            ))
    if len(observations) < MAX_OBSERVATIONS:
        cancelled_count = sum(cancellations.values())
        if cancelled_count >= MIN_POSTPONES:
            observations.append(Observation(
                f"Observed: {cancelled_count} task cancellations were recorded in "
                f"the last {WINDOW_DAYS} days. Cancellations can reflect changing plans."
            ))

    completed_tasks = [
        task for task in tasks
        if task.status == StatusEnum.completed
        and _as_aware(task.completed_at) is not None
        and _as_aware(task.completed_at) >= since
    ]
    if len(completed_tasks) >= MIN_COMPLETIONS_FOR_RATE:
        observations.append(Observation(
            f"Observed: {len(completed_tasks)} tasks were completed in the last "
            f"{WINDOW_DAYS} days. This is a count, not a judgment."
        ))

    low_or_overwhelmed_days = set()
    for item in checkins:
        reflection = item.reflection or ""
        if (item.mood is not None and item.mood <= 2) or OVERWHELM_CUES.search(reflection):
            stamp = _as_aware(item.created_at)
            if stamp:
                low_or_overwhelmed_days.add(stamp.astimezone(local_zone).date())
    postponed_days = {
        stamp.astimezone(local_zone).date()
        for row in rows
        if row.task_id is not None
        and row.event_type == "not_now"
        and (stamp := _as_aware(row.occurred_at)) is not None
    }
    coincident_days = low_or_overwhelmed_days & postponed_days
    if len(coincident_days) >= 2:
        observations.append(Observation(
            f"Observed: on {len(coincident_days)} days in the last {WINDOW_DAYS} days, "
            "a Check-in recording low mood or overwhelm and a task postponement occurred "
            "on the same local date. This is a timing overlap only; it does not show "
            "that one caused the other."
        ))

    def known_deadline(task):
        return (
            task.due_date is not None
            and getattr(task, "due_date_is_all_day", None) is not None
            and _as_aware(task.completed_at) is not None
        )

    recent_start = now - timedelta(days=7)
    previous_start = now - timedelta(days=14)
    recent_known = [
        task for task in completed_tasks
        if known_deadline(task) and _as_aware(task.completed_at) >= recent_start
    ]
    previous_known = [
        task for task in completed_tasks
        if known_deadline(task)
        and previous_start <= _as_aware(task.completed_at) < recent_start
    ]
    if len(recent_known) >= 3 and len(previous_known) >= 3:
        recent_late = sum(
            _as_aware(task.completed_at) > _as_aware(task.due_date)
            for task in recent_known
        )
        previous_late = sum(
            _as_aware(task.completed_at) > _as_aware(task.due_date)
            for task in previous_known
        )
        observations.append(Observation(
            f"Observed: {recent_late} of {len(recent_known)} tasks with known deadlines "
            f"completed late in the last 7 days, compared with {previous_late} of "
            f"{len(previous_known)} in the 7 days before that. This comparison does not "
            "establish why outcomes changed."
        ))

    if not observations:
        return BehaviorFacts(
            "found" if checkins else "none_found",
            "Behavioral observations: recorded events exist, but none meet the minimum "
            "evidence threshold for a repeated pattern. Do not invent postponement "
            "or productivity claims.\n"
            + "\n".join(checkin_lines),
        )

    observations = observations[:MAX_OBSERVATIONS]
    prompt = render_observations(observations) + "\n" + "\n".join(checkin_lines)
    return BehaviorFacts(
        "found", prompt, observation_count=len(observations), observations=observations
    )
