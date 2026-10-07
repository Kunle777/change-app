import os
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://test:test@127.0.0.1:5432/change_app_test",
)

from app.ai import action_service  # noqa: E402
from app.ai import tool_executor  # noqa: E402


class FakeResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def scalars(self):
        return self

    def all(self):
        return self.value


class FakeSession:
    def __init__(self, result=None):
        self.execute = AsyncMock(return_value=FakeResult(result))
        self.add = Mock()
        self.flush = AsyncMock()
        self.commit = AsyncMock()
        self.rollback = AsyncMock()


class AIActionTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_tool_auto_executes_without_staging_confirmation(self):
        user = SimpleNamespace(id=uuid.uuid4())
        db = FakeSession()
        with patch.object(
            action_service,
            "execute_tool",
            new=AsyncMock(return_value={"status": "created", "task_id": "task-id"}),
        ) as execute:
            result = await action_service.handle_tool_call(
                db, user, uuid.uuid4(), "create_task", {"title": "Call mum"}
            )

        self.assertEqual(result["status"], "created")
        execute.assert_awaited_once()
        db.commit.assert_awaited_once()
        db.add.assert_not_called()

    async def test_update_tool_stages_confirmation_instead_of_executing(self):
        user = SimpleNamespace(id=uuid.uuid4())
        db = FakeSession()
        with patch.object(
            action_service,
            "validate_confirmation_tool",
            new=AsyncMock(return_value=({"task_id": str(uuid.uuid4()), "priority": "high"}, "Update task.")),
        ), patch.object(action_service, "execute_tool", new=AsyncMock()) as execute:
            result = await action_service.handle_tool_call(
                db,
                user,
                uuid.uuid4(),
                "update_task",
                {"task_id": str(uuid.uuid4()), "priority": "high"},
            )

        self.assertEqual(result["status"], "awaiting_confirmation")
        self.assertIsNotNone(result["pending_action_id"])
        execute.assert_not_awaited()
        db.add.assert_called_once()
        db.flush.assert_awaited_once()
        db.commit.assert_awaited_once()

    async def test_expired_confirmation_never_executes(self):
        pending = SimpleNamespace(
            id=uuid.uuid4(),
            status="pending",
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
        user = SimpleNamespace(id=uuid.uuid4())
        db = FakeSession(pending)
        with patch.object(action_service, "execute_tool", new=AsyncMock()) as execute:
            result = await action_service.confirm_pending_action(db, user, pending.id)

        self.assertEqual(result["status"], "expired")
        self.assertEqual(pending.status, "expired")
        execute.assert_not_awaited()
        db.commit.assert_awaited_once()

    async def test_successful_confirmation_commits_mutation_and_status_once(self):
        pending = SimpleNamespace(
            id=uuid.uuid4(),
            status="pending",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            tool_name="update_task",
            arguments={"task_id": str(uuid.uuid4()), "priority": "high"},
        )
        user = SimpleNamespace(id=uuid.uuid4())
        db = FakeSession(pending)
        with patch.object(
            action_service,
            "execute_tool",
            new=AsyncMock(return_value={"status": "updated", "task_id": pending.arguments["task_id"]}),
        ) as execute:
            result = await action_service.confirm_pending_action(db, user, pending.id)

        self.assertEqual(result["status"], "updated")
        self.assertEqual(pending.status, "confirmed")
        execute.assert_awaited_once()
        db.commit.assert_awaited_once()
        db.rollback.assert_not_awaited()

    async def test_confirmed_action_cannot_execute_twice(self):
        pending = SimpleNamespace(
            id=uuid.uuid4(),
            status="pending",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            tool_name="update_task",
            arguments={"task_id": str(uuid.uuid4()), "priority": "high"},
        )
        user = SimpleNamespace(id=uuid.uuid4())
        db = FakeSession(pending)
        db.execute.side_effect = [FakeResult(pending), FakeResult(None)]
        with patch.object(
            action_service,
            "execute_tool",
            new=AsyncMock(return_value={"status": "updated", "task_id": pending.arguments["task_id"]}),
        ) as execute:
            first = await action_service.confirm_pending_action(db, user, pending.id)
            second = await action_service.confirm_pending_action(db, user, pending.id)

        self.assertEqual(first["status"], "updated")
        self.assertEqual(second["status"], "error")
        execute.assert_awaited_once()
        db.commit.assert_awaited_once()

    async def test_stale_proposal_does_not_mutate_task(self):
        task = SimpleNamespace(
            id=uuid.uuid4(),
            title="Write report",
            due_date=None,
            priority=tool_executor.PriorityEnum.medium,
        )
        user = SimpleNamespace(id=uuid.uuid4())
        db = FakeSession()
        with patch.object(
            tool_executor.task_service,
            "get_task_by_id",
            new=AsyncMock(return_value=task),
        ), patch.object(
            tool_executor.task_service,
            "update_task",
            new=AsyncMock(),
        ) as update:
            result = await tool_executor.execute_tool(
                db,
                user,
                "update_task",
                {
                    "task_id": str(task.id),
                    "priority": "high",
                    "_expected_state": {"due_date": None, "priority": "low"},
                },
            )

        self.assertEqual(result["status"], "stale")
        update.assert_not_awaited()

    async def test_confirmation_rolls_back_task_mutation_if_status_flip_fails(self):
        pending = SimpleNamespace(
            id=uuid.uuid4(),
            status="pending",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            tool_name="update_task",
            arguments={"task_id": str(uuid.uuid4()), "priority": "high"},
        )
        user = SimpleNamespace(id=uuid.uuid4())
        task_state = {"changed": False}

        async def fail_after_mutation(*args, **kwargs):
            task_state["changed"] = True
            raise RuntimeError("simulated failure before confirmation commit")

        async def rollback_transaction():
            task_state["changed"] = False

        db = FakeSession(pending)
        db.rollback.side_effect = rollback_transaction
        with patch.object(action_service, "execute_tool", side_effect=fail_after_mutation):
            with self.assertRaisesRegex(RuntimeError, "simulated failure"):
                await action_service.confirm_pending_action(db, user, pending.id)

        self.assertFalse(task_state["changed"])
        self.assertEqual(pending.status, "pending")
        db.rollback.assert_awaited_once()
        db.commit.assert_not_awaited()

    async def test_update_tool_rejects_task_not_owned_by_user(self):
        user = SimpleNamespace(id=uuid.uuid4())
        db = FakeSession()
        task_id = uuid.uuid4()
        with patch.object(tool_executor.task_service, "get_task_by_id", new=AsyncMock(return_value=None)):
            result = await tool_executor.execute_tool(
                db,
                user,
                "update_task",
                {"task_id": str(task_id), "priority": "high"},
            )

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["reason"], "Task not found or not yours")


if __name__ == "__main__":
    unittest.main()
