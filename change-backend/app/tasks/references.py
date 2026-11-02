import hashlib
import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.tasks.models import Task


_TASK_REFERENCE = re.compile(r"^tk_[0-9a-f]{64}$")


def opaque_task_reference(user_id: uuid.UUID, task_id: uuid.UUID) -> str:
    digest = hashlib.sha256(f"{user_id}:{task_id}".encode()).hexdigest()
    return f"tk_{digest}"


async def resolve_task_reference(
    db: AsyncSession, user_id: uuid.UUID, reference: str
) -> uuid.UUID | None:
    if not _TASK_REFERENCE.fullmatch(reference):
        return None
    result = await db.execute(
        select(Task.id).where(
            Task.user_id == user_id,
            Task.is_deleted.is_(False),
        )
    )
    for task_id in result.scalars().all():
        if reference == opaque_task_reference(user_id, task_id):
            return task_id
    return None
