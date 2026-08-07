import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.checkins.models import CheckIn, CheckInType
from app.checkins.schemas import CheckInCreate, CheckInResponse, MorningCheckInCreate, EveningCheckInCreate
from typing import Union, List
async def get_checkin_by_id(db: AsyncSession, checkin_id: uuid.UUID, user_id: uuid.UUID):
    result = await db.execute(select(CheckIn).where(CheckIn.id == checkin_id, CheckIn.user_id == user_id))
    return result.scalar_one_or_none()

async def create_checkin(db: AsyncSession, checkin_data: Union[MorningCheckInCreate, EveningCheckInCreate], user_id: uuid.UUID, checkin_type: CheckInType):
    db_checkin = CheckIn(
        user_id=user_id,
        type=checkin_type,
        **checkin_data.model_dump(exclude_unset=True)
    )
    db.add(db_checkin)
    await db.commit()
    await db.refresh(db_checkin)
    return db_checkin

async def get_checkin_history(db: AsyncSession, user_id: uuid.UUID, limit: int = 20) -> List[CheckIn]:
    result = await db.execute(select(CheckIn).where(CheckIn.user_id == user_id).order_by(CheckIn.created_at.desc()).limit(limit))
    return list(result.scalars().all())