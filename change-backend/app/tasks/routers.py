import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.users.models import User
from app.users.dependencies import get_current_user
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
from app.tasks.references import opaque_task_reference, resolve_task_reference
from app.ai.safe_text import redact_internal_identifiers
from app.tasks.task_event_service import log_task_event
from app.ai import service as ai_service
from app.tasks.voice_parse import parse_voice_task
from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Literal, Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

router = APIRouter(
    prefix="/api/tasks",
    tags=["Tasks"],
)


def _serialize_task(task: Any, user_id: uuid.UUID) -> dict[str, Any]:
    response = TaskResponse(
        id=opaque_task_reference(user_id, task.id),
        title=task.title,
        priority=task.priority,
        status=task.status,
        description=task.description,
        due_date=task.due_date,
        due_date_is_all_day=task.due_date_is_all_day,
        reminder_time=task.reminder_time,
        priority_reminder=task.priority_reminder,
        recurrence=task.recurrence,
        has_series=task.series_id is not None,
        occurrence_date=task.occurrence_date,
        created_at=task.created_at,
    ).model_dump()
    response["title"] = redact_internal_identifiers(response["title"])
    response["description"] = (
        redact_internal_identifiers(response["description"])
        if response["description"] is not None
        else None
    )
    return response


async def _resolve_task_id(
    reference: str, db: AsyncSession, user_id: uuid.UUID
) -> uuid.UUID:
    task_id = await resolve_task_reference(db, user_id, reference)
    if task_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task_id


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
    if isinstance(result.get("title"), str):
        result["title"] = redact_internal_identifiers(result["title"])
    return result


@router.get("/upcoming", response_model=list[TaskResponse])
async def get_upcoming_tasks_route(
    days: int = Query(default=14, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tasks = await service.get_upcoming_tasks(db, current_user.id, days)
    return [_serialize_task(task, current_user.id) for task in tasks]


@router.get("/undated", response_model=list[TaskResponse])
async def get_undated_tasks_route(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tasks = await service.get_undated_tasks(db, current_user.id)
    return [_serialize_task(task, current_user.id) for task in tasks]


@router.post("", response_model=TaskResponse)
async def create_task_route(
    data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user:User = Depends(get_current_user),
):
    
    task = await service.create_task(db, data, current_user.id)
    return _serialize_task(task, current_user.id)
class OverdueResponse(BaseModel):
    count: int
    tasks: list[TaskResponse]


@router.get("/overdue", response_model=OverdueResponse)
async def get_overdue_tasks_route(
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await service.get_overdue_tasks(
        db,
        current_user.id,
        current_user.last_active_timezone,
        limit=limit,
    )
    return {
        "count": result["count"],
        "tasks": [_serialize_task(task, current_user.id) for task in result["tasks"]],
    }
@router.get("", response_model=list[TaskResponse])
async def get_tasks_route(
    db:AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tasks = await service.get_tasks_for_user(db, current_user.id)
    return [_serialize_task(task, current_user.id) for task in tasks]

@router.get("/calendar-dates", response_model=CalendarDatesResponse)
async def calendar_dates(
    year: int,
    month: int,
    timezone_name: str | None = Query(default=None, alias="timezone"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if timezone_name is not None:
        try:
            ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="timezone must be a valid IANA time zone",
            ) from error
    dates = await service.get_task_dates_for_month(
        db, current_user.id, year, month, timezone_name or current_user.last_active_timezone
    )
    return {"dates": dates}


@router.get("/by-date", response_model=list[TaskResponse])
async def tasks_by_date(
    date: str,
    task_status: str = Query(default="all", alias="status"),
    timezone_name: str | None = Query(default=None, alias="timezone"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    target = datetime.strptime(date, "%Y-%m-%d").date()
    if timezone_name is not None:
        try:
            ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="timezone must be a valid IANA time zone",
            ) from error
    tasks = await service.get_tasks_for_date(
        db,
        current_user.id,
        target,
        task_status,
        timezone_name or current_user.last_active_timezone,
    )
    return [_serialize_task(task, current_user.id) for task in tasks]

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task_route(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task_id = await _resolve_task_id(task_id, db, current_user.id)
    result = await service.get_task_by_id(db, task_id, current_user.id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return _serialize_task(result, current_user.id)

@router.patch("/{task_id}", response_model=TaskResponse)
async def patch_task_route(
    task_id: str,
    data: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task_id = await _resolve_task_id(task_id, db, current_user.id)
    result= await service.update_task(db, task_id, data, current_user.id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return _serialize_task(result, current_user.id)
@router.post("/{task_id}/done", response_model=TaskResponse)
async def complete_task_route(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task_id = await _resolve_task_id(task_id, db, current_user.id)
    result = await service.mark_task_completed(db, task_id, current_user.id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return _serialize_task(result, current_user.id)

@router.delete("/{task_id}")
async def delete_task_route(
    task_id: str,
    db:AsyncSession = Depends(get_db),
    current_user: User= Depends(get_current_user),
):
    task_id = await _resolve_task_id(task_id, db, current_user.id)
    result= await service.delete_task(db, task_id, current_user.id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return {"message": "Task deleted successfully"}

@router.post("/{task_id}/snooze", response_model=TaskResponse)
async def snooze_task_route(
    task_id: str,
    payload: TaskSnooze | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task_id = await _resolve_task_id(task_id, db, current_user.id)
    result = await service.snooze_task(
        db,
        task_id,
        current_user.id,
        payload.snoozed_until if payload else None,
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return _serialize_task(result, current_user.id)


@router.post("/{task_id}/events", status_code=status.HTTP_202_ACCEPTED)
async def record_client_task_event_route(
    task_id: str,
    payload: ClientTaskEventRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task_id = await _resolve_task_id(task_id, db, current_user.id)
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
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task_id = await _resolve_task_id(task_id, db, current_user.id)
    await ai_service.check_usage(db, current_user.id)

    try:
        steps = await service.breakdown_task(db, task_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    await ai_service.increment_usage(db, current_user.id)
    return steps

@router.patch("/{task_id}/reschedule", response_model=TaskResponse)
async def reschedule_task_route(
    task_id: str,
    payload: TaskReschedule,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task_id = await _resolve_task_id(task_id, db, current_user.id)
    result = await service.reschedule_task(
        db, task_id, current_user.id, payload.due_date, payload.reminder_time,
        payload.due_date_is_all_day,
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return _serialize_task(result, current_user.id)

@router.post("/{task_id}/cancel", response_model=TaskResponse)
async def cancel(
    task_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task_id = await _resolve_task_id(task_id, db, current_user.id)
    result = await service.cancel_task(db, task_id, current_user.id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return _serialize_task(result, current_user.id)


@router.post("/{task_id}/stop-series")
async def stop_series(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task_id = await _resolve_task_id(task_id, db, current_user.id)
    stopped = await service.stop_task_series(db, task_id, current_user.id)
    if not stopped:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurring series not found")
    return {"stopped": True}


@router.patch("/{task_id}/series-edit", response_model=TaskResponse)
async def edit_series(
    task_id: str,
    payload: SeriesEditRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task_id = await _resolve_task_id(task_id, db, current_user.id)
    result = await service.edit_task_series(db, task_id, current_user.id, payload)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if result is False:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Task is not linked to a recurring series")
    return _serialize_task(result, current_user.id)
