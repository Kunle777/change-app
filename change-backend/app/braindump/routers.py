import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.users.models import User
from app.users.dependencies import get_current_user
from app.braindump.schemas import BrainDumpCreate, BrainDumpResponse
from app.braindump import service
from app.tasks.schemas import TaskResponse

router = APIRouter(prefix="/api/braindump", tags=["Brain Dump"])


# Import the response schema into the module namespace explicitly for FastAPI decorators.
TaskResponseModel = TaskResponse

@router.post("", response_model=BrainDumpResponse)
async def create_dump_route(data: BrainDumpCreate, db=Depends(get_db), current_user=Depends(get_current_user)):
    return await service.create_brain_dump(db, data, current_user.id)

@router.get("", response_model=list[BrainDumpResponse])
async def get_dumps_route(db=Depends(get_db), current_user=Depends(get_current_user)):
    return await service.get_brain_dumps_for_user(db, current_user.id)

@router.delete("/{dump_id}")
async def delete_dump_route(dump_id: uuid.UUID, db=Depends(get_db), current_user=Depends(get_current_user)):
    result = await service.delete_brain_dump(db, dump_id, current_user.id)
    if result is None:
        raise HTTPException(status_code=404, detail="Brain dump not found")
    return {"message": "Deleted successfully"}

@router.post("/{dump_id}/convert", response_model=TaskResponseModel)
async def convert_dump_route(dump_id: uuid.UUID, db=Depends(get_db), current_user=Depends(get_current_user)):
    result = await service.convert_to_task(db, dump_id, current_user.id)
    if result is None:
        raise HTTPException(status_code=404, detail="Brain dump not found")
    return result

@router.post("/{task_id}/breakdown", response_model=list[str])
async def breakdown_task_route(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await ai_service.check_usage(db, current_user.id)

    try:
        steps = await service.breakdown_task(db, task_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    await ai_service.increment_usage(db, current_user.id)
    return steps