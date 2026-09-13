from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.users.models import User
from app.users.entitlements_models import FeatureEntitlements


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