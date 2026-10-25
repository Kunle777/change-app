from dataclasses import dataclass

from sqlalchemy import text


@dataclass(frozen=True)
class MemoryAccess:
    allowed: bool
    reason: str  # ok | no_user | ai_disabled | memory_off


async def ai_processing_allowed(db, user_id) -> MemoryAccess:
    """Whether the account may call the AI coach. Missing entitlements default to allowed."""
    row = (await db.execute(text(
        "SELECT f.ai_enabled FROM users u "
        "LEFT JOIN feature_entitlements f ON f.user_id = u.id "
        "WHERE u.id = :u"
    ), {"u": user_id})).first()
    if row is None:
        return MemoryAccess(False, "no_user")
    if row[0] is False:
        return MemoryAccess(False, "ai_disabled")
    return MemoryAccess(True, "ok")


async def memory_access(db, user_id) -> MemoryAccess:
    """The single permission decision for indexing, search, and browse."""
    row = (await db.execute(text(
        "SELECT u.personal_memory_enabled, f.ai_enabled "
        "FROM users u LEFT JOIN feature_entitlements f ON f.user_id = u.id "
        "WHERE u.id = :u"
    ), {"u": user_id})).first()
    if row is None:
        return MemoryAccess(False, "no_user")
    memory_on, ai_on = row
    if ai_on is False:
        return MemoryAccess(False, "ai_disabled")
    if not memory_on:
        return MemoryAccess(False, "memory_off")
    return MemoryAccess(True, "ok")


async def purge_user_memory(db, user_id) -> int:
    """Delete derived chunks only; original Brain Dumps and check-ins remain."""
    result = await db.execute(
        text("DELETE FROM memory_chunks WHERE user_id = :u"), {"u": user_id}
    )
    return result.rowcount or 0


async def set_personal_memory(db, user_id, enabled: bool) -> dict:
    await db.execute(
        text("UPDATE users SET personal_memory_enabled = :enabled WHERE id = :u"),
        {"enabled": enabled, "u": user_id},
    )
    purged = 0 if enabled else await purge_user_memory(db, user_id)
    await db.commit()
    return {"enabled": enabled, "purged": purged}
