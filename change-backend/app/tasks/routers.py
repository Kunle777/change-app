import uuid
from fastapi import APIRouter, Depends, HTTPException,status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.users.models import User
from app.users.dependencies import get_current_user
from app.tasks.schemas import TaskCreate, TaskResponse, TaskUpdate, TaskReschedule
from app.tasks import service
from app.tasks.models import StatusEnum
from app.ai import service as ai_service

router = APIRouter(
    prefix="/api/tasks",
    tags=["Tasks"],
)

@router.post("", response_model=TaskResponse)
async def create_task_route(
    data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user:User = Depends(get_current_user),
):
    
    return await service.create_task(db,data, current_user.id)
@router.get("/overdue", response_model=TaskResponse)
async def get_overdue_tasks_route(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    overdue_tasks = await service.get_overdue_tasks(db, current_user.id)
    return overdue_tasks
@router.get("", response_model=list[TaskResponse])
async def get_tasks_route(
    db:AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await service.get_tasks_for_user(db, current_user.id)

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task_route(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await service.get_task_by_id(db, task_id, current_user.id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return result

@router.patch("/{task_id}", response_model=TaskResponse)
async def patch_task_route(
    task_id: uuid.UUID,
    data: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result= await service.update_task(db, task_id, data, current_user.id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return result
@router.post("/{task_id}/done", response_model=TaskResponse)
async def complete_task_route(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await service.mark_task_completed(db, task_id, current_user.id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return result

@router.delete("/{task_id}")
async def delete_task_route(
    task_id: uuid.UUID,
    db:AsyncSession = Depends(get_db),
    current_user: User= Depends(get_current_user),
):
    result= await service.delete_task(db, task_id, current_user.id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return {"message": "Task deleted successfully"}

@router.post("/{task_id}/snooze", response_model=TaskResponse)
async def snooze_task_route(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await service.snooze_task(db, task_id, current_user.id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
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

@router.patch("/{task_id}/reschedule", response_model=TaskResponse)
async def reschedule_task_route(
    task_id: uuid.UUID,
    payload: TaskReschedule,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await service.reschedule_task(
        db, task_id, current_user.id, payload.due_date, payload.reminder_time
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return result

@router.post("/{task_id}/cancel", response_model=TaskResponse)
async def cancel(
    task_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.cancel_task(db, task_id, current_user.id)