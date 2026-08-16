import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.braindump.models import BrainDump
from app.braindump.schemas import BrainDumpCreate
from app.tasks.models import Task, PriorityEnum
from app.tasks.schemas import TaskCreate
from app.tasks.service import create_task
from app.ai import gemini


async def create_brain_dump(db: AsyncSession, brain_dump: BrainDumpCreate, user_id: uuid.UUID):
    db_brain_dump = BrainDump(
        user_id=user_id,
        content=brain_dump.content,
        is_converted=False,
    )
    db.add(db_brain_dump)
    await db.commit()
    await db.refresh(db_brain_dump)
    return db_brain_dump


async def get_brain_dumps_for_user(db: AsyncSession, user_id: uuid.UUID):
    result = await db.execute(select(BrainDump).where(BrainDump.user_id == user_id))
    return result.scalars().all()


async def get_brain_dump_by_id(db: AsyncSession, brain_dump_id: uuid.UUID, user_id: uuid.UUID):
    result = await db.execute(
        select(BrainDump).where(
            and_(BrainDump.id == brain_dump_id, BrainDump.user_id == user_id)
        )
    )
    return result.scalars().first()


async def delete_brain_dump(db: AsyncSession, brain_dump_id: uuid.UUID, user_id: uuid.UUID):
    brain_dump = await get_brain_dump_by_id(db, brain_dump_id, user_id)
    if not brain_dump:
        return None
    await db.delete(brain_dump)
    await db.commit()
    return brain_dump


PRIORITY_MAP = {"low": PriorityEnum.low, "medium": PriorityEnum.medium, "high": PriorityEnum.high}


async def convert_to_task(db: AsyncSession, dump_id: uuid.UUID, user_id: uuid.UUID):
    dump = await get_brain_dump_by_id(db, dump_id, user_id)
    if not dump:
        return None

    prompt = (
        "The following is a raw, unstructured note a user quickly dictated or typed. "
        "Identify each distinct actionable task mentioned. If there is only one task, "
        "return an array with one item. If there are none (e.g. it's just a thought, "
        "not an action), return an empty array.\n\n"
        f"Raw note: \"{dump.content}\"\n\n"
        "Respond with ONLY a JSON array of objects, each with exactly two fields: "
        "\"title\" (short, action-oriented, under 10 words) and "
        "\"priority\" (one of: \"low\", \"medium\", \"high\" — infer from urgency words "
        "like 'asap', 'today', 'whenever'; default to \"medium\" if unclear). "
        "No extra text, no markdown."
    )

    try:
        raw = gemini.generate_structured(prompt)
        parsed = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            title = item.get("title")
            priority = item.get("priority", "medium")
            if not title or not isinstance(title, str):
                continue
            if priority not in PRIORITY_MAP:
                priority = "medium"
            parsed.append({"title": title.strip(), "priority": priority})
    except Exception:
        parsed = [{"title": dump.content[:200], "priority": "medium"}]

    if not parsed:
        parsed = [{"title": dump.content[:200], "priority": "medium"}]

    created_tasks = []
    for item in parsed:
        task = await create_task(
            db,
            TaskCreate(title=item["title"], priority=PRIORITY_MAP[item["priority"]]),
            user_id,
        )
        created_tasks.append(task)

    dump.is_converted = True
    await db.commit()

    return created_tasks
