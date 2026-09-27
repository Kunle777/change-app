import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.Users.models import User
from app.Users.dependencies import get_current_user
from app.braindump.schemas import (
    BrainDumpCreate,
    BrainDumpResponse,
    ConvertRequest,
    ParseDumpResponse,
)
from app.braindump import service
from app.tasks.schemas import TaskResponse
from app.ai import service as ai_service

router = APIRouter(prefix="/api/braindump", tags=["Brain Dump"])

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

@router.post("/{dump_id}/parse", response_model=ParseDumpResponse)
async def parse_dump_route(dump_id: uuid.UUID, db=Depends(get_db), current_user=Depends(get_current_user)):
    try:
        await ai_service.check_usage(db, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e))

    try:
        result = await service.parse_dump(db, dump_id, current_user.id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
    if result is None:
        raise HTTPException(status_code=404, detail="Brain dump not found")
    await ai_service.increment_usage(db, current_user.id)
    return {"suggestions": result}


@router.post("/{dump_id}/convert", response_model=list[TaskResponseModel])
async def convert_dump_route(
    dump_id: uuid.UUID,
    data: ConvertRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    suggestions = [item.model_dump() for item in data.suggestions]
    result = await service.convert_to_task(db, dump_id, current_user.id, suggestions)
    if result is None:
        raise HTTPException(status_code=404, detail="Brain dump not found")

    return result
