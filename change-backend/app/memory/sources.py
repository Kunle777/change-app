import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.models import AIInteraction
from app.braindump.models import BrainDump
from app.checkins.models import CheckIn
from app.memory.chunking import chunk_text

CONVERSATION_SOURCE = "conversation_user"
_GREETING = re.compile(
    r"^(hi|hello|hey|thanks|thank you|ok|okay|yes|no|good morning|good night|gm|gn)\b",
    re.I,
)
_SHORT_TASK_COMMAND = re.compile(
    r"\b(add|create|schedule|set|move|cancel|delete|complete)\b.{0,40}\b(task|reminder)\b",
    re.I,
)


def is_indexable_user_message(text: str) -> bool:
    """Keep user-authored chat text that could be useful later; skip chatter and commands."""
    cleaned = (text or "").strip()
    if len(cleaned) < 40 or len(cleaned.split()) < 8:
        return False
    if _GREETING.match(cleaned):
        return False
    if _SHORT_TASK_COMMAND.search(cleaned) and len(cleaned) < 100:
        return False
    return True


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
    for_update: bool = False,
) -> tuple[list[str], datetime, datetime] | None:
    """Load only the user's original text, never model-generated summaries."""
    if source_type == "brain_dump":
        statement = select(BrainDump).where(
            BrainDump.id == source_id,
            BrainDump.user_id == user_id,
        )
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        row = (await db.execute(statement)).scalar_one_or_none()
        if row is None:
            return None
        texts = chunk_text(row.content)
        return texts, _aware(row.created_at), _aware(row.updated_at)

    if source_type == "check_in":
        statement = select(CheckIn).where(
            CheckIn.id == source_id,
            CheckIn.user_id == user_id,
        )
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        row = (await db.execute(statement)).scalar_one_or_none()
        if row is None:
            return None
        texts = check_in_texts(
            kind=row.type,
            mood=row.mood,
            goal_today=row.goal_today,
            goal_status=row.goal_status,
            reflection=row.reflection,
        )
        return texts, _aware(row.created_at), _aware(row.updated_at)

    if source_type == CONVERSATION_SOURCE:
        statement = select(AIInteraction).where(
            AIInteraction.id == source_id,
            AIInteraction.user_id == user_id,
        )
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        row = (await db.execute(statement)).scalar_one_or_none()
        if row is None:
            return None
        created = _aware(row.created_at) if row.created_at else datetime.now(timezone.utc)
        if not is_indexable_user_message(row.question):
            return [], created, created
        texts = chunk_text(row.question)
        return texts, created, created

    raise ValueError(f"Unknown memory source type: {source_type}")
