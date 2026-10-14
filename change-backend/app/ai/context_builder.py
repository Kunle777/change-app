from sqlalchemy.ext.asyncio import AsyncSession
from app.tasks.models import StatusEnum
from app.tasks.service import get_tasks_for_user

async def build_context(db: AsyncSession, user_id, intent: str) -> str:
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
        return "Open tasks:\n" + "\n".join(lines)

    if intent == "pattern_reflection":
        return "No detailed behavioral history is available yet to identify patterns."

    return "No specific ELVYN data is needed for this message."