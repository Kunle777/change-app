"""Offline harness: builds the real coaching context for a scripted scenario and
returns it so a case can assert on exactly what Gemini would receive.

No database and no model call: every source loader is replaced with canned data, but
planning, budgeting, tool policy and prompt assembly are the real code.
"""
import os
import uuid
from contextlib import ExitStack
from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://test:test@127.0.0.1:5432/change_app_test",
)

from app.ai import context_service  # noqa: E402
from app.ai.behavior import BehaviorFacts, Observation, render_observations  # noqa: E402
from app.ai.task_context import TaskFacts, TaskGroup, render_groups  # noqa: E402
from app.memory.retrieval import RetrievalResult, RetrievedMemory  # noqa: E402

T0 = datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc)


def memory_result(*texts, source_type="brain_dump", state="found"):
    memories = [
        RetrievedMemory(source_type, f"src-{i}", text, T0, 0.8) for i, text in enumerate(texts)
    ]
    return RetrievalResult(state, memories, mode="vector")


def task_facts(open_titles=(), events=()):
    groups = []
    if open_titles:
        groups.append(
            TaskGroup(
                "other_open", 0.2, "Other open tasks:",
                [f'- id: {uuid.uuid4()}; title: "{t}"; status: pending' for t in open_titles], 2,
            )
        )
    if events:
        groups.append(TaskGroup("events", 3.0, "Recorded task events:", list(events)))
    else:
        groups.append(TaskGroup("events_none", 3.0, "No recorded postponement, reschedule, cancellation, or completion events in the last 30 days.", []))
    return TaskFacts("found", render_groups(groups), len(open_titles), 0, len(events), True, groups)


def behavior_found(*pairs):
    items = [Observation(text, subject) for text, subject in pairs]
    return BehaviorFacts("found", render_observations(items), len(items), items)


@dataclass
class Scenario:
    message: str
    history: list[tuple[str, str]] = field(default_factory=list)  # (question, response)
    open_titles: tuple[str, ...] = ()
    tasks: TaskFacts | None = None
    behavior: BehaviorFacts | None = None
    memory: RetrievalResult | None = None


async def run_scenario(scenario: Scenario):
    turns = [
        SimpleNamespace(id=uuid.uuid4(), question=q, response=r) for q, r in scenario.history
    ]
    freshness = SimpleNamespace(
        to_prompt_line=lambda: "Data freshness: test.", tier=SimpleNamespace(value="rich")
    )
    retrieve = AsyncMock(return_value=scenario.memory or RetrievalResult("none_found", mode="vector"))
    load_tasks = AsyncMock(return_value=scenario.tasks or task_facts(scenario.open_titles))
    load_behavior = AsyncMock(return_value=scenario.behavior or BehaviorFacts("none_found", "Behavioral observations: not enough recorded task events. Do not invent patterns."))
    with ExitStack() as stack:
        stack.enter_context(patch.object(context_service, "resolve_user_timezone", AsyncMock(return_value=ZoneInfo("Africa/Lagos"))))
        stack.enter_context(patch.object(context_service, "compute_data_freshness", AsyncMock(return_value=freshness)))
        stack.enter_context(patch.object(context_service, "load_recent_turns", AsyncMock(return_value=turns)))
        stack.enter_context(patch.object(context_service, "load_open_task_titles", AsyncMock(return_value=list(scenario.open_titles))))
        stack.enter_context(patch.object(context_service, "load_task_facts", load_tasks))
        stack.enter_context(patch.object(context_service, "load_behavior_observations", load_behavior))
        stack.enter_context(patch.object(context_service, "retrieve_memories", retrieve))
        context = await context_service.assemble_coaching_context(
            SimpleNamespace(),
            user_id=uuid.uuid4(),
            message=scenario.message,
            conversation_id=uuid.uuid4(),
            timezone_name="Africa/Lagos",
        )
    return context, SimpleNamespace(retrieve=retrieve, load_tasks=load_tasks, load_behavior=load_behavior)
