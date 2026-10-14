import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.tasks.models import TaskEvent
from app.checkins.models import CheckIn
from app.braindump.models import BrainDump


class FreshnessTier(str, Enum):
    FRESH = "fresh"       # activity within the last 2 days
    AGING = "aging"       # 3-7 days
    STALE = "stale"       # 8-21 days
    DORMANT = "dormant"   # 22+ days or never


@dataclass
class DataFreshness:
    days_since_task_activity: int | None
    days_since_checkin: int | None
    days_since_brain_dump: int | None
    tier: FreshnessTier

    def to_prompt_line(self) -> str:
        """
        Turns the signal into a plain-English line for the system prompt.
        Deliberately factual, not editorializing — the model forms its own
        tone from this, it doesn't need to be told how to feel about it.
        """
        parts = []
        parts.append(
            f"tasks: {self._describe(self.days_since_task_activity)}"
        )
        parts.append(
            f"check-ins: {self._describe(self.days_since_checkin)}"
        )
        parts.append(
            f"brain dumps: {self._describe(self.days_since_brain_dump)}"
        )
        return "Recent activity — " + "; ".join(parts) + "."

    @staticmethod
    def _describe(days: int | None) -> str:
        if days is None:
            return "no history yet"
        if days == 0:
            return "today"
        if days == 1:
            return "1 day ago"
        return f"{days} days ago"


async def _days_since(db: AsyncSession, stmt) -> int | None:
    result = await db.execute(stmt)
    most_recent = result.scalar_one_or_none()
    if most_recent is None:
        return None
    delta = datetime.now(timezone.utc) - most_recent
    return max(delta.days, 0)


async def compute_data_freshness(db: AsyncSession, user_id: uuid.UUID) -> DataFreshness:
    days_tasks = await _days_since(
        db,
        select(func.max(TaskEvent.occurred_at)).where(TaskEvent.user_id == user_id),
    )
    days_checkin = await _days_since(
        db,
        select(func.max(CheckIn.created_at)).where(CheckIn.user_id == user_id),
    )
    days_dump = await _days_since(
        db,
        select(func.max(BrainDump.created_at)).where(BrainDump.user_id == user_id),
    )

    # Overall tier takes the FRESHEST of the three signals, not the stalest —
    # a user who's actively logging tasks but skipping check-ins shouldn't be
    # treated as fully dormant just because one channel is quiet.
    best = min(
        (d for d in (days_tasks, days_checkin, days_dump) if d is not None),
        default=None,
    )
    tier = _tier_for(best)

    return DataFreshness(
        days_since_task_activity=days_tasks,
        days_since_checkin=days_checkin,
        days_since_brain_dump=days_dump,
        tier=tier,
    )


def _tier_for(days: int | None) -> FreshnessTier:
    if days is None:
        return FreshnessTier.DORMANT
    if days <= 2:
        return FreshnessTier.FRESH
    if days <= 7:
        return FreshnessTier.AGING
    if days <= 21:
        return FreshnessTier.STALE
    return FreshnessTier.DORMANT