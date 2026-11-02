import logging
import re
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.checkins.models import CheckIn
from app.memory.retrieval import sanitize_for_prompt

logger = logging.getLogger(__name__)
_DIRECT_CHECKIN = re.compile(
    r"\b(check-?ins?|check in)\b", re.I
)


@dataclass(frozen=True)
class CheckInFacts:
    state: str
    prompt: str


def is_direct_checkin_question(message: str) -> bool:
    text = (message or "").lower()
    return bool(_DIRECT_CHECKIN.search(text)) and bool(
        re.search(r"\b(what|which|show|tell|said|wrote|today|yesterday|last|details?)\b", text)
    )


async def load_checkin_facts(
    db: AsyncSession,
    user_id: UUID,
    message: str,
    timezone_name: str | None,
    *,
    now: datetime | None = None,
) -> CheckInFacts:
    zone = ZoneInfo(timezone_name or "Africa/Lagos")
    local_now = (now or datetime.now(timezone.utc)).astimezone(zone)
    local_day = local_now.date()
    text = (message or "").lower()
    try:
        if "yesterday" in text:
            local_day -= timedelta(days=1)
        elif "today" not in text and "this morning" not in text and "tonight" not in text:
            result = await db.execute(
                select(CheckIn)
                .where(CheckIn.user_id == user_id)
                .order_by(CheckIn.created_at.desc())
                .limit(5)
            )
            records = list(result.scalars().all())
            if not records:
                return CheckInFacts("none_found", "Original check-in records: none found.")
            return CheckInFacts("found", _render_records(records, zone))

        start = datetime.combine(local_day, time.min, tzinfo=zone).astimezone(timezone.utc)
        end = datetime.combine(local_day + timedelta(days=1), time.min, tzinfo=zone).astimezone(timezone.utc)
        result = await db.execute(
            select(CheckIn)
            .where(
                CheckIn.user_id == user_id,
                CheckIn.created_at >= start,
                CheckIn.created_at < end,
            )
            .order_by(CheckIn.created_at.asc())
        )
        records = list(result.scalars().all())
    except Exception:
        logger.exception("Direct check-in source retrieval failed")
        return CheckInFacts(
            "unavailable",
            "Original check-in records could not be retrieved because of a technical issue. "
            "Do not infer whether a check-in exists.",
        )
    if not records:
        return CheckInFacts("none_found", f"Original check-in records: none found for {local_day.isoformat()}.")
    return CheckInFacts("found", _render_records(records, zone))


def _render_records(records: list[CheckIn], zone: ZoneInfo) -> str:
    lines = ["Original check-in records (user-authored source data):"]
    for record in records:
        created_at = record.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        local_time = created_at.astimezone(zone).strftime("%Y-%m-%d %H:%M")
        mood = f"{record.mood}/5" if record.mood is not None else "not recorded"
        lines.append(f"- {record.type.value} at {local_time}; mood: {mood}")
        for label, value in (
            ("goal", record.goal_today),
            ("goal status", record.goal_status),
            ("reflection", record.reflection),
        ):
            if value:
                lines.append(f"  {label}: {sanitize_for_prompt(value, 500)}")
    return "\n".join(lines)
