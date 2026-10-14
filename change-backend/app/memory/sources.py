import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.braindump.models import BrainDump
from app.checkins.models import CheckIn
from app.memory.chunking import chunk_text


MOOD_LABELS = {1: "very low", 2: "low", 3: "okay", 4: "good", 5: "great"}


def _value(value):
    return getattr(value, "value", value)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def check_in_texts(
    *,
    kind,
    mood: int | None,
    goal_today: str | None,
    goal_status: str | None,
    reflection: str | None,
) -> list[str]:
    goal = (goal_today or "").strip()
    reflected = (reflection or "").strip()
    if not goal and not reflected:
        return []

    parts = [f"{str(_value(kind)).capitalize()} check-in."]
    if mood in MOOD_LABELS:
        parts.append(f"Mood: {MOOD_LABELS[mood]} ({mood}/5).")
    if goal:
        parts.append(f"Goal: {goal}.")
    if goal_status:
        parts.append(f"Goal status: {_value(goal_status)}.")
    if reflected:
        parts.append(f"Reflection: {reflected}")
    return chunk_text(" ".join(parts))


async def load_source(
    db: AsyncSession,
    *,
    source_type: str,
    source_id: uuid.UUID,
    user_id: uuid.UUID,
) -> tuple[list[str], datetime] | None:
    """Load only the user's original text, never model-generated summaries."""
    if source_type == "brain_dump":
        row = (
            await db.execute(
                select(BrainDump).where(
                    BrainDump.id == source_id,
                    BrainDump.user_id == user_id,
                )
            )
        ).scalar_one_or_none()
        if row is None:
            return None
        texts = chunk_text(row.content)
        return texts, _aware(row.created_at)

    if source_type == "check_in":
        row = (
            await db.execute(
                select(CheckIn).where(
                    CheckIn.id == source_id,
                    CheckIn.user_id == user_id,
                )
            )
        ).scalar_one_or_none()
        if row is None:
            return None
        texts = check_in_texts(
            kind=row.type,
            mood=row.mood,
            goal_today=row.goal_today,
            goal_status=row.goal_status,
            reflection=row.reflection,
        )
        return texts, _aware(row.created_at)

    raise ValueError(f"Unknown memory source type: {source_type}")
