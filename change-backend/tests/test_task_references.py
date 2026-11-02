import os
import unittest
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://127.0.0.1:5432/change_app_test",
)

from app.tasks.references import opaque_task_reference, resolve_task_reference  # noqa: E402
from app.tasks.routers import _serialize_task  # noqa: E402
from app.tasks.schemas import TaskResponse  # noqa: E402


class ScalarResult:
    def __init__(self, values):
        self.values = values

    def scalars(self):
        return self

    def all(self):
        return self.values


class TaskReferenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_reference_is_opaque_and_owner_scoped(self):
        user_id = uuid.uuid4()
        other_user_id = uuid.uuid4()
        task_id = uuid.uuid4()
        db = SimpleNamespace(execute=AsyncMock(return_value=ScalarResult([task_id])))
        reference = opaque_task_reference(user_id, task_id)

        self.assertTrue(reference.startswith("tk_"))
        self.assertNotIn(str(task_id), reference)
        self.assertEqual(
            await resolve_task_reference(db, user_id, reference),
            task_id,
        )
        self.assertIsNone(
            await resolve_task_reference(db, other_user_id, reference),
        )

    async def test_invalid_and_unknown_references_do_not_resolve(self):
        task_id = uuid.uuid4()
        db = SimpleNamespace(execute=AsyncMock(return_value=ScalarResult([task_id])))

        self.assertIsNone(await resolve_task_reference(db, uuid.uuid4(), str(task_id)))
        self.assertIsNone(
            await resolve_task_reference(db, uuid.uuid4(), "tk_" + "0" * 64),
        )

    def test_serialized_task_has_no_database_ids_and_redacts_ids_in_user_text(self):
        user_id = uuid.uuid4()
        task_id = uuid.uuid4()
        title_id = str(uuid.uuid4())
        task = SimpleNamespace(
            id=task_id,
            user_id=user_id,
            title=f"Call client {title_id}",
            description=f"Reference task id: 123 at 3:30 on 2026-03-11",
            priority=SimpleNamespace(name="high"),
            status=SimpleNamespace(name="pending"),
            due_date=datetime(2026, 3, 11, 15, 30, tzinfo=timezone.utc),
            due_date_is_all_day=False,
            reminder_time=None,
            priority_reminder=False,
            recurrence=None,
            series_id=uuid.uuid4(),
            occurrence_date=None,
            created_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        )

        serialized = _serialize_task(task, user_id)
        rendered = TaskResponse.model_validate(serialized).model_dump_json()

        self.assertEqual(serialized["id"], opaque_task_reference(user_id, task_id))
        self.assertNotIn(str(task_id), rendered)
        self.assertNotIn(str(task.series_id), rendered)
        self.assertNotIn(str(user_id), rendered)
        self.assertNotIn(title_id, rendered)
        self.assertNotIn("user_id", serialized)
        self.assertNotIn("series_id", serialized)
        self.assertTrue(serialized["has_series"])
        self.assertIn("3:30", rendered)
        self.assertIn("2026-03-11", rendered)


if __name__ == "__main__":
    unittest.main()
