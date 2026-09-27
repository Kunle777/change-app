import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.Users.models import User
from app.Users.dependencies import get_current_user
from app.tasks.schemas import (
    CalendarDatesResponse,
    SeriesEditRequest,
    TaskCreate,
    TaskReschedule,
    TaskResponse,
    TaskSnooze,
    TaskUpdate,
)
from app.tasks import service
from app.tasks.models import StatusEnum, TaskEvent, TaskEventOutbox, TaskEventType
from app.tasks.task_event_service import log_task_event
from app.ai import service as ai_service
from app.tasks.voice_parse import parse_voice_task
from pydantic import BaseModel, Field
from datetime import date, datetime as dt
from typing import Literal

router = APIRouter(
    prefix="/api/tasks",
    tags=["Tasks"],
)


class VoiceParseRequest(BaseModel):
    transcript: str = Field(min_length=1, max_length=1000)
    today: date | None = None


class ClientTaskEventRequest(BaseModel):
    event_type: Literal["reminder_scheduled", "reminder_opened"]
    reminder_time: datetime | None = None
    notification_id: str | None = Field(default=None, max_length=255)


@router.post("/parse-voice")
async def parse_voice_task_route(
    payload: VoiceParseRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        await ai_service.check_usage(db, current_user.id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(error))
    result = await parse_voice_task(payload.transcript, payload.today)
    await ai_service.increment_usage(db, current_user.id)
    return result


@router.get("/upcoming", response_model=list[TaskResponse])
async def get_upcoming_tasks_route(
    days: int = Query(default=14, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await service.get_upcoming_tasks(db, current_user.id, days)

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

@router.get("/calendar-dates", response_model=CalendarDatesResponse)
async def calendar_dates(
    year: int,
    month: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    dates = await service.get_task_dates_for_month(db, current_user.id, year, month)
    return {"dates": dates}


@router.get("/by-date", response_model=list[TaskResponse])
async def tasks_by_date(
    date: str,
    status: str = "all",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    target = dt.strptime(date, "%Y-%m-%d").date()
    return await service.get_tasks_for_date(db, current_user.id, target, status)

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
    payload: TaskSnooze | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await service.snooze_task(
        db,
        task_id,
        current_user.id,
        payload.snoozed_until if payload else None,
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return result


@router.post("/{task_id}/events", status_code=status.HTTP_202_ACCEPTED)
async def record_client_task_event_route(
    task_id: uuid.UUID,
    payload: ClientTaskEventRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await service.get_task_by_id(db, task_id, current_user.id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    event_type = TaskEventType(payload.event_type)
    if not payload.notification_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Notification ID is required")
    metadata = {"notification_id": payload.notification_id}
    if event_type == TaskEventType.REMINDER_SCHEDULED:
        if payload.reminder_time is None or task.reminder_time is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="A scheduled reminder time is required")
        if payload.reminder_time != task.reminder_time:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reminder time no longer matches the task")
        metadata["reminder_time"] = payload.reminder_time.isoformat()
    else:
        for event_model in (TaskEvent, TaskEventOutbox):
            duplicate = await db.execute(
                select(event_model.id).where(
                    event_model.user_id == current_user.id,
                    event_model.task_id == task.id,
                    event_model.event_type == event_type.value,
                    event_model.event_metadata["notification_id"].astext == payload.notification_id,
                ).limit(1)
            )
            if duplicate.scalar_one_or_none() is not None:
                return {"accepted": True, "duplicate": True}

    await log_task_event(
        db,
        user_id=current_user.id,
        task_id=task.id,
        event_type=event_type,
        metadata=metadata,
    )
    await db.commit()
    return {"accepted": True}

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


@router.post("/{task_id}/stop-series")
async def stop_series(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stopped = await service.stop_task_series(db, task_id, current_user.id)
    if not stopped:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurring series not found")
    return {"stopped": True}


@router.patch("/{task_id}/series-edit", response_model=TaskResponse)
async def edit_series(
    task_id: uuid.UUID,
    payload: SeriesEditRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await service.edit_task_series(db, task_id, current_user.id, payload)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if result is False:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Task is not linked to a recurring series")
    return result
