import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.users.models import User
from app.users.dependencies import get_current_user
from app.tasks.schemas import TaskCreate, TaskResponse
from app.tasks import service

router = APIRouter(
    prefix="/tasks",
    tags=["Tasks"],
)

@router.post("", response_model=TaskResponse)
async def create_task_route(
    data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user:User = Depends(get_current_user),
):
    
    return await service.create_task(db,data, current_user.id)

@router.get("", response_model=list[TaskResponse])
async def get_tasks_route(
    db:AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await service.get_tasks_for_user(db, current_user.id)