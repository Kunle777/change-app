from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, or_, select

from app.braindump.models import BrainDump
from app.checkins.models import CheckIn
from app.memory.sources import check_in_texts


@dataclass
class BrowseEntry:
    source_type: str
    source_id: str
    text: str
    created_at: datetime


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


async def browse_entries(db, *, user_id, since=None, until=None,
                         limit: int = 8) -> tuple[list[BrowseEntry], int]:
    """List original text entries in a date range, newest first, with the full count."""
    dump_where = [BrainDump.user_id == user_id, func.length(func.trim(BrainDump.content)) > 0]
    has_text = or_(
        func.length(func.trim(func.coalesce(CheckIn.goal_today, ""))) > 0,
        func.length(func.trim(func.coalesce(CheckIn.reflection, ""))) > 0,
    )
    checkin_where = [CheckIn.user_id == user_id, has_text]
    if since is not None:
        dump_where.append(BrainDump.created_at >= since)
        checkin_where.append(CheckIn.created_at >= since)
    if until is not None:
        dump_where.append(BrainDump.created_at < until)
        checkin_where.append(CheckIn.created_at < until)

    dumps = (await db.execute(
        select(BrainDump).where(*dump_where).order_by(BrainDump.created_at.desc(), BrainDump.id).limit(limit)
    )).scalars().all()
    checkins = (await db.execute(
        select(CheckIn).where(*checkin_where).order_by(CheckIn.created_at.desc(), CheckIn.id).limit(limit)
    )).scalars().all()
    total = (
        (await db.execute(select(func.count()).select_from(BrainDump).where(*dump_where))).scalar_one()
        + (await db.execute(select(func.count()).select_from(CheckIn).where(*checkin_where))).scalar_one()
    )
    entries = [BrowseEntry("brain_dump", str(d.id), d.content, _aware(d.created_at)) for d in dumps]
    for checkin in checkins:
        texts = check_in_texts(
            kind=checkin.type, mood=checkin.mood, goal_today=checkin.goal_today,
            goal_status=checkin.goal_status, reflection=checkin.reflection,
        )
        if texts:
            entries.append(BrowseEntry("check_in", str(checkin.id), " ".join(texts), _aware(checkin.created_at)))
    entries.sort(key=lambda entry: entry.created_at, reverse=True)
    return entries[:limit], total
