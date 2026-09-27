import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.Users.dependencies import get_current_user
from app.checkins.models import CheckInType
from app.checkins.schemas import CheckInResponse, MorningCheckInCreate, EveningCheckInCreate
from app.checkins import service
from app.Users.models import User

router = APIRouter(
    prefix="/api/checkins",
    tags=["Check-ins"],
)

@router.post("/morning", response_model=CheckInResponse)
async def create_morning_checkin_route(
    data: MorningCheckInCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await service.create_checkin(db, data, current_user.id, CheckInType.morning)

@router.post("/evening", response_model=CheckInResponse)
async def create_evening_checkin_route(
    data: EveningCheckInCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await service.create_checkin(db, data, current_user.id, CheckInType.evening)

@router.get("/history", response_model=list[CheckInResponse])
async def get_checkin_history_route(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 20
):
    return await service.get_checkin_history(db, current_user.id, limit)


@router.get("/today-status")
async def get_today_status_route(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await service.get_todays_checkin_status(db, current_user)