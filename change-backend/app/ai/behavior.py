import logging
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.retrieval import sanitize_for_prompt
from app.tasks.models import StatusEnum, Task, TaskEvent, TaskEventOutbox

WINDOW_DAYS = 30
MIN_POSTPONES = 3
MIN_DEADLINE_MOVES = 2
MIN_COMPLETIONS_FOR_RATE = 5
MAX_OBSERVATIONS = 6
MAX_CHARS = 1200
logger = logging.getLogger(__name__)


@dataclass
class BehaviorFacts:
    state: str
    prompt: str
    observation_count: int = 0


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
    now: datetime | None = None,
) -> BehaviorFacts:
    if not needed:
        return BehaviorFacts("not_needed", "")

    now = now or datetime.now(timezone.utc)
    since = now - timedelta(days=WINDOW_DAYS)
    try:
        event_query = union_all(
            select(
                TaskEvent.task_id,
                TaskEvent.event_type,
                TaskEvent.occurred_at,
                TaskEvent.event_metadata,
            ).where(
                TaskEvent.user_id == user_id,
                TaskEvent.occurred_at >= since,
                TaskEvent.event_type.in_(
                    ("not_now", "rescheduled", "deadline_changed", "completed")
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
                    ("not_now", "rescheduled", "deadline_changed", "completed")
                ),
            ),
        )
        rows = (await db.execute(event_query)).all()
        tasks = (
            await db.execute(
                select(Task).where(
                    Task.user_id == user_id,
                    Task.is_deleted.is_(False),
                    Task.created_at >= since,
                )
            )
        ).scalars().all()
    except Exception:
        logger.warning("Behavioral observations failed", exc_info=True)
        return BehaviorFacts("unavailable", "")

    if not rows and not tasks:
        return BehaviorFacts(
            "none_found",
            "Behavioral observations: not enough recorded task events in the last "
            f"{WINDOW_DAYS} days to describe a pattern. Lack of recorded activity "
            "is not evidence that the user did nothing.",
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
    completions = []
    for row in rows:
        if row.task_id is None:
            continue
        if row.event_type == "not_now":
            postpones[row.task_id] += 1
        elif row.event_type in {"deadline_changed", "rescheduled"}:
            deadline_moves[row.task_id] += 1
        elif row.event_type == "completed":
            completions.append(_as_aware(row.occurred_at) or now)

    observations: list[str] = []
    for task_id, count in postpones.most_common():
        if count < MIN_POSTPONES:
            continue
        title = titles.get(task_id, "a task")
        observations.append(
            f'Observed: "{title}" has {count} recorded postponements ("not now") '
            f"in the last {WINDOW_DAYS} days."
        )
        if len(observations) >= MAX_OBSERVATIONS:
            break

    if len(observations) < MAX_OBSERVATIONS:
        for task_id, count in deadline_moves.most_common():
            if count < MIN_DEADLINE_MOVES:
                continue
            title = titles.get(task_id, "a task")
            observations.append(
                f'Observed: "{title}" had {count} recorded deadline changes or '
                f"reschedules in the last {WINDOW_DAYS} days."
            )
            if len(observations) >= MAX_OBSERVATIONS:
                break

    created = [task for task in tasks]
    completed_tasks = [
        task for task in created if task.status == StatusEnum.completed
    ]
    if len(completed_tasks) >= MIN_COMPLETIONS_FOR_RATE:
        observations.append(
            f"Observed: {len(completed_tasks)} of {len(created)} tasks created in the "
            f"last {WINDOW_DAYS} days are currently marked completed. This is a count, "
            "not a judgment."
        )

    midpoint = now - timedelta(days=7)
    recent = [stamp for stamp in completions if stamp and stamp >= midpoint]
    previous = [stamp for stamp in completions if stamp and stamp < midpoint]
    if len(completions) >= MIN_COMPLETIONS_FOR_RATE:
        observations.append(
            f"Observed: {len(recent)} recorded completions in the last 7 days versus "
            f"{len(previous)} in the 7 days before that."
        )

    if not observations:
        return BehaviorFacts(
            "none_found",
            "Behavioral observations: recorded events exist, but none meet the minimum "
            "evidence threshold for a repeated pattern. Do not invent postponement "
            "or productivity claims.",
        )

    body = "\n".join(f"- {item}" for item in observations[:MAX_OBSERVATIONS])
    prompt = (
        "Behavioral observations (derived from recorded task events only; "
        "these are observations, not diagnoses or character labels):\n"
        f"{body}"
    )
    if len(prompt) > MAX_CHARS:
        prompt = prompt[: MAX_CHARS - 1].rstrip() + "…"
    return BehaviorFacts("found", prompt, observation_count=len(observations))
