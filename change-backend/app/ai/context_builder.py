from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from app.tasks.models import StatusEnum
from app.tasks.service import get_tasks_for_user


async def build_context(db: AsyncSession, user_id, intent: str) -> str:
    today = datetime.now(timezone.utc).date()

    if intent in ("task_planning", "task_help", "daily_review"):
        tasks = await get_tasks_for_user(db, user_id)
        tasks = [
            task
            for task in tasks
            if task.status in (StatusEnum.pending, StatusEnum.in_progress)
        ][:40]
        if not tasks:
            return "The user has no open tasks."
        lines = [
            f"- id: {t.id}; title: {t.title}; priority: {t.priority.name}; "
            f"status: {t.status.name}; due_date: {t.due_date.isoformat() if t.due_date else 'not set'}"
            for t in tasks
        ]
        return f"Open tasks (today is {today.isoformat()}):\n" + "\n".join(lines)

    if intent == "pattern_reflection":
        # No task_events table yet (Phase 6) — be honest about that limit for now.
        return "No behavioral history is available yet to identify patterns."

    return "No specific ELVYN data is needed for this message."
