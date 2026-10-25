from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.behavior import load_behavior_observations
from app.ai.intent_router import plan_sources
from app.ai.task_context import load_task_facts


async def build_context(db: AsyncSession, user_id, intent: str) -> str:
    plan = plan_sources("", intent)
    if not plan.need_tasks and not plan.need_events and not plan.need_behavior:
        return "No specific ELVYN data is needed for this message."
    facts = await load_task_facts(
        db,
        user_id,
        need_tasks=plan.need_tasks,
        need_events=plan.need_events,
    )
    behavior = await load_behavior_observations(db, user_id, needed=plan.need_behavior)
    parts = [part for part in (facts.prompt, behavior.prompt) if part]
    return "\n\n".join(parts) if parts else "No specific ELVYN data is needed for this message."