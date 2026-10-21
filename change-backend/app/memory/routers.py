from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.memory.policy import memory_access, set_personal_memory
from app.users.dependencies import get_current_user
from app.users.models import User

router = APIRouter(prefix="/api/memory", tags=["memory"])


class MemorySetting(BaseModel):
    enabled: bool


@router.get("/settings", summary="Whether ELVYN may remember my saved entries")
async def get_memory_settings(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    access = await memory_access(db, user.id)
    return {
        "enabled": bool(user.personal_memory_enabled),
        "effective": access.allowed,
        "reason": access.reason,
    }


@router.patch("/settings", summary="Turn personal memory on or off; off deletes derived memory")
async def update_memory_settings(
    payload: MemorySetting,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await set_personal_memory(db, user.id, payload.enabled)
