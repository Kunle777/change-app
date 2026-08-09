import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.braindump.models import BrainDump
from app.braindump.schemas import BrainDumpCreate, BrainDumpResponse
from datetime import datetime, timedelta,timezone
from app.tasks.models import Task
from app.tasks.schemas import TaskCreate, TaskResponse
from app.tasks.service import create_task


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

async def convert_to_task(db: AsyncSession, dump_id: uuid.UUID, user_id: uuid.UUID):
    dump = await get_brain_dump_by_id(db, dump_id, user_id)
    if not dump:
        return None

    task_data = TaskCreate(title=dump.content)
    new_task = await create_task(db, task_data, user_id)

    dump.is_converted = True
    await db.commit()

    return new_task