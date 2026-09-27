from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.users.models import User
from app.users.entitlements_models import FeatureEntitlements


async def record_daily_activity(db: AsyncSession, user_id, timezone_name: str) -> dict:
    """Count at most one active day for the user's device-local calendar date."""
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as error:
        raise ValueError("timezone must be a valid IANA time zone") from error
    today = datetime.now(zone).date()
    result = await db.execute(select(User).where(User.id == user_id).with_for_update())
    user = result.scalar_one()
    last_active = user.last_active_date
    if last_active != today:
        user.current_streak = user.current_streak + 1 if last_active == today - timedelta(days=1) else 1
        user.longest_streak = max(user.longest_streak, user.current_streak)
        user.last_active_date = today
        user.last_active_timezone = timezone_name
        await db.commit()
        await db.refresh(user)
    return {
        "current_streak": user.current_streak,
        "longest_streak": user.longest_streak,
        "last_active_date": user.last_active_date.isoformat() if user.last_active_date else None,
        "timezone": user.last_active_timezone,
    }


async def get_activity_streak(db: AsyncSession, user_id) -> dict:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    return {
        "current_streak": user.current_streak,
        "longest_streak": user.longest_streak,
        "last_active_date": user.last_active_date.isoformat() if user.last_active_date else None,
        "timezone": user.last_active_timezone,
    }


async def update_fcm_token(db: AsyncSession, user: User, token: str) -> User:
    user.fcm_token = token
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_or_create_entitlements(db: AsyncSession, user_id) -> FeatureEntitlements:
    result = await db.execute(
        select(FeatureEntitlements).where(FeatureEntitlements.user_id == user_id)
    )
    ent = result.scalar_one_or_none()
    if ent is None:
        ent = FeatureEntitlements(user_id=user_id)
        db.add(ent)
        await db.commit()
        await db.refresh(ent)
    return ent


async def set_country_code(
    db: AsyncSession, user_id, country_code: str
) -> FeatureEntitlements:
    country_code = country_code.upper()

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    user.country_code = country_code

    ent = await get_or_create_entitlements(db, user_id)
    # This is the actual enforcement point: server-side, stored, not
    # re-derived from device locale/GPS on every request.
    ent.savings_enabled = country_code == "NG"

    await db.commit()
    await db.refresh(ent)
    return ent
