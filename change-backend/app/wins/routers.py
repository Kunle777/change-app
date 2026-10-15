from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.users.dependencies import get_current_user
from app.users.models import User
from app.wins.schemas import WinCreate, WinResponse
from app.wins import service

router = APIRouter(prefix="/api/wins", tags=["Wins"])


@router.post("", response_model=WinResponse)
async def create_win_route(
    payload: WinCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await service.create_win(db, current_user.id, payload)


@router.get("", response_model=list[WinResponse])
async def get_wins_route(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await service.get_wins(db, current_user.id)


@router.get("/streak")
async def get_streak_route(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    streak = await service.get_current_streak(db, current_user.id)
    return {"streak": streak}
