from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from app.tasks.service import get_tasks_for_date


async def build_context(db: AsyncSession, user_id, intent: str) -> str:
    today = datetime.now(timezone.utc).date()

    if intent in ("task_planning", "task_help", "daily_review"):
        tasks = await get_tasks_for_date(db, user_id, today, "all")
        if not tasks:
            return "The user has no tasks scheduled for today."
        lines = [
            f"- {t.title} (priority: {t.priority}, status: {t.status})"
            for t in tasks
        ]
        return "Today's tasks:\n" + "\n".join(lines)

    if intent == "pattern_reflection":
        # No task_events table yet (Phase 6) — be honest about that limit for now.
        return "No behavioral history is available yet to identify patterns."

    return "No specific ELVYN data is needed for this message."