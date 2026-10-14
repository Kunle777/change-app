import logging
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from app.braindump.models import BrainDump
from app.checkins.models import CheckIn
from app.tasks.models import Task, TaskEvent, TaskEventOutbox
from app.users.models import User

logger = logging.getLogger(__name__)
DEFAULT_TIMEZONE = "Africa/Lagos"


class FreshnessTier(str, Enum):
    FRESH = "fresh"
    AGING = "aging"
    STALE = "stale"
    DORMANT = "dormant"


@dataclass
class DataFreshness:
    days_since_task_activity: int | None
    days_since_checkin: int | None
    days_since_brain_dump: int | None
    tier: FreshnessTier

    def to_prompt_line(self) -> str:
        parts = [
            f"tasks: {self._describe(self.days_since_task_activity)}",
            f"check-ins: {self._describe(self.days_since_checkin)}",
            f"brain dumps: {self._describe(self.days_since_brain_dump)}",
        ]
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


async def resolve_user_timezone(
    db: AsyncSession,
    user_id: uuid.UUID,
    timezone_name: str | None = None,
) -> ZoneInfo:
    if timezone_name:
        try:
            return ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            logger.warning("Invalid user timezone; trying the stored timezone")

    result = await db.execute(
        select(User.last_active_timezone).where(User.id == user_id)
    )
    stored_timezone = result.scalar_one_or_none()
    if stored_timezone:
        try:
            return ZoneInfo(stored_timezone)
        except ZoneInfoNotFoundError:
            logger.warning("Invalid stored user timezone; using %s", DEFAULT_TIMEZONE)

    return ZoneInfo(DEFAULT_TIMEZONE)


def _days_since(
    most_recent: datetime | None,
    user_timezone: ZoneInfo,
    local_today: date,
) -> int | None:
    if most_recent is None:
        return None
    if most_recent.tzinfo is None:
        most_recent = most_recent.replace(tzinfo=timezone.utc)
    activity_date = most_recent.astimezone(user_timezone).date()
    return max((local_today - activity_date).days, 0)


async def _latest_activity_days(
    db: AsyncSession,
    statement,
    user_timezone: ZoneInfo,
    local_today: date,
) -> int | None:
    result = await db.execute(statement)
    return _days_since(result.scalar_one_or_none(), user_timezone, local_today)


async def compute_data_freshness(
    db: AsyncSession,
    user_id: uuid.UUID,
    timezone_name: str | None = None,
) -> DataFreshness:
    user_timezone = await resolve_user_timezone(db, user_id, timezone_name)
    local_today = datetime.now(user_timezone).date()

    task_activity = union_all(
        select(TaskEvent.occurred_at.label("activity_at")).where(
            TaskEvent.user_id == user_id
        ),
        select(TaskEventOutbox.occurred_at.label("activity_at")).where(
            TaskEventOutbox.user_id == user_id
        ),
        select(Task.created_at.label("activity_at")).where(Task.user_id == user_id),
        select(Task.completed_at.label("activity_at")).where(
            Task.user_id == user_id,
            Task.completed_at.is_not(None),
        ),
        select(Task.deleted_at.label("activity_at")).where(
            Task.user_id == user_id,
            Task.deleted_at.is_not(None),
        ),
    ).subquery("task_activity")

    days_tasks = await _latest_activity_days(
        db,
        select(func.max(task_activity.c.activity_at)),
        user_timezone,
        local_today,
    )
    days_checkin = await _latest_activity_days(
        db,
        select(func.max(CheckIn.created_at)).where(CheckIn.user_id == user_id),
        user_timezone,
        local_today,
    )
    days_dump = await _latest_activity_days(
        db,
        select(func.max(BrainDump.created_at)).where(BrainDump.user_id == user_id),
        user_timezone,
        local_today,
    )

    best = min(
        (days for days in (days_tasks, days_checkin, days_dump) if days is not None),
        default=None,
    )
    return DataFreshness(
        days_since_task_activity=days_tasks,
        days_since_checkin=days_checkin,
        days_since_brain_dump=days_dump,
        tier=_tier_for(best),
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
