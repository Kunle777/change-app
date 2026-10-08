import unittest
import uuid
from datetime import date, datetime, time, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from app.braindump.schemas import ParsedTaskSuggestion
from app.braindump.detector import looks_like_possible_task
from app.braindump.service import convert_to_task
from app.tasks.models import Task
from app.tasks.service import _local_day_start_utc


class FakeSession:
    def __init__(self, dump):
        self.dump = dump
        self.added = []
        self.flush = AsyncMock()
        self.commit = AsyncMock()
        self.refresh = AsyncMock()

    async def execute(self, _query):
        result = Mock()
        result.scalar_one_or_none.return_value = self.dump
        return result

    def add(self, value):
        self.added.append(value)


class BrainDumpConversionTests(unittest.IsolatedAsyncioTestCase):
    def test_possible_task_detector_recognizes_by_hour_intent(self):
        self.assertTrue(looks_like_possible_task("i want to sing by 12 om"))

    def test_local_day_boundary_uses_user_timezone(self):
        self.assertEqual(
            _local_day_start_utc("Africa/Lagos", date(2026, 10, 20)),
            datetime(2026, 10, 19, 23, tzinfo=timezone.utc),
        )

    async def test_edited_local_date_and_time_are_saved_to_task(self):
        user_id = uuid.uuid4()
        dump = SimpleNamespace(id=uuid.uuid4(), is_converted=False, created_task_id=None)
        db = FakeSession(dump)
        suggestion = ParsedTaskSuggestion(
            title="Prepare presentation",
            priority="high",
            due_date=date(2026, 10, 20),
            time=time(9, 30),
        )

        with patch("app.braindump.service.log_task_event", new_callable=AsyncMock):
            tasks = await convert_to_task(
                db,
                dump.id,
                user_id,
                [suggestion.model_dump()],
                "Africa/Lagos",
            )

        self.assertEqual(len(tasks), 1)
        task = tasks[0]
        self.assertIsInstance(task, Task)
        self.assertEqual(
            task.due_date,
            datetime(2026, 10, 20, 22, 59, 59, 999999, tzinfo=timezone.utc),
        )
        self.assertEqual(
            task.reminder_time,
            datetime(2026, 10, 20, 8, 30, tzinfo=timezone.utc),
        )
        self.assertEqual(task.priority.name, "high")


if __name__ == "__main__":
    unittest.main()
