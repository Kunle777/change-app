import os
import unittest
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://test:test@127.0.0.1:5432/change_app_test",
)

from app.ai import action_service  # noqa: E402
from app.ai.intent_router import plan_sources  # noqa: E402
from app.ai.tool_policy import CONFIRMATION_PROMPT_NOTE, decide_tools  # noqa: E402
from app.memory.retrieval import MEMORY_RULES, RetrievalResult, RetrievedMemory  # noqa: E402

T0 = datetime(2026, 10, 1, tzinfo=timezone.utc)
FOUND = RetrievalResult(
    "found", [RetrievedMemory("brain_dump", "a", "entry", T0, 0.8)], mode="vector"
)
NONE = RetrievalResult("none_found", mode="vector")


class FakeSession:
    def __init__(self):
        self.execute = AsyncMock()
        self.add = Mock()
        self.flush = AsyncMock()
        self.commit = AsyncMock()
        self.rollback = AsyncMock()


class DecisionTests(unittest.TestCase):
    def test_no_action_intent_means_no_tools_even_without_memory(self):
        d = decide_tools(plan_sources("What should I do today?"), NONE)
        self.assertFalse(d.offer_tools)

    def test_action_without_memory_is_offered_immediately(self):
        d = decide_tools(plan_sources("Add a task to call mum tomorrow"), RetrievalResult("not_needed"))
        self.assertTrue(d.offer_tools)
        self.assertFalse(d.require_confirmation)

    def test_memory_does_not_block_a_legitimate_action_but_forces_confirmation(self):
        plan = plan_sources("Remind me to send the portfolio, like I mentioned last week")
        d = decide_tools(plan, FOUND)
        self.assertTrue(plan.need_memory and plan.action_intent)
        self.assertTrue(d.offer_tools)
        self.assertTrue(d.require_confirmation)

    def test_memory_alone_never_enables_tools(self):
        d = decide_tools(plan_sources("Do you remember what I told you about my goals?"), FOUND)
        self.assertFalse(d.offer_tools)

    def test_out_of_scope_gets_no_tools(self):
        self.assertFalse(decide_tools(plan_sources("write me a python script"), NONE).offer_tools)

    def test_prompt_wording(self):
        self.assertNotIn("cannot create or change tasks", MEMORY_RULES)
        self.assertIn("current message", MEMORY_RULES)
        self.assertIn("confirmation", CONFIRMATION_PROMPT_NOTE)


class ForcedConfirmationTests(unittest.IsolatedAsyncioTestCase):
    async def test_forced_create_is_staged_not_executed(self):
        user = SimpleNamespace(id=uuid.uuid4(), last_active_timezone="Africa/Lagos")
        db = FakeSession()
        with patch.object(action_service, "execute_tool", new=AsyncMock()) as execute:
            result = await action_service.handle_tool_call(
                db, user, uuid.uuid4(), "create_task",
                {"title": "Send portfolio", "due_date": "2026-10-30"},
                force_confirmation=True,
            )
        self.assertEqual(result["status"], "awaiting_confirmation")
        self.assertIn("Send portfolio", result["summary"])
        execute.assert_not_awaited()
        pending = db.add.call_args.args[0]
        self.assertEqual(pending.tool_name, "create_task")
        self.assertEqual(pending.arguments["title"], "Send portfolio")

    async def test_unforced_create_still_auto_executes(self):
        user = SimpleNamespace(id=uuid.uuid4())
        db = FakeSession()
        with patch.object(
            action_service, "execute_tool",
            new=AsyncMock(return_value={"status": "created", "task_id": "x"}),
        ) as execute:
            result = await action_service.handle_tool_call(
                db, user, uuid.uuid4(), "create_task", {"title": "Call mum"}
            )
        self.assertEqual(result["status"], "created")
        execute.assert_awaited_once()

    async def test_forced_create_still_validates_arguments(self):
        user = SimpleNamespace(id=uuid.uuid4(), last_active_timezone="Africa/Lagos")
        db = FakeSession()
        result = await action_service.handle_tool_call(
            db, user, uuid.uuid4(), "create_task", {"title": "  "}, force_confirmation=True
        )
        self.assertEqual(result["status"], "error")
        db.add.assert_not_called()
        result = await action_service.handle_tool_call(
            db, user, uuid.uuid4(), "create_task",
            {"title": "ok", "task_id": "injected"}, force_confirmation=True,
        )
        self.assertEqual(result["status"], "error")

    async def test_unknown_tool_is_rejected_even_when_forced(self):
        user = SimpleNamespace(id=uuid.uuid4())
        result = await action_service.handle_tool_call(
            FakeSession(), user, uuid.uuid4(), "complete_task", {}, force_confirmation=True
        )
        self.assertEqual(result["status"], "error")


if __name__ == "__main__":
    unittest.main()
