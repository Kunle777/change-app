from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from app.tasks.models import StatusEnum
from app.tasks.service import get_tasks_for_user
from app.ai.freshness_service import compute_data_freshness
from app.users.models import User

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

async def build_system_prompt(db: AsyncSession, user: User) -> str:
    freshness = await compute_data_freshness(db, user.id)

    base_prompt = (
        "You are Elvyn, a calm, grounded personal coach. "
        "Only use the context explicitly given to you below — never invent "
        "details about the user's tasks, check-ins, or history that aren't "
        "present in this context."
    )

    freshness_note = (
        f"\n\n{freshness.to_prompt_line()} "
        "If recent activity is sparse or absent in an area, say so honestly "
        "rather than assuming or inventing what might have happened."
    )

    # ... existing personality/tone/RAG-context assembly from Phase 5 stays here ...

    return base_prompt + freshness_note  # + whatever else build_system_prompt already returns