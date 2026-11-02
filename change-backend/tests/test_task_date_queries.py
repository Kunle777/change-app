import os
import unittest
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://127.0.0.1:5432/change_app_test",
)

from app.tasks.service import get_tasks_for_date  # noqa: E402
from app.users.service import record_daily_activity  # noqa: E402


class Result:
    def __init__(self, value):
        self.value = value

    def scalars(self):
        return self

    def all(self):
        return self.value

    def scalar_one(self):
        return self.value


class TaskDateQueryTests(unittest.IsolatedAsyncioTestCase):
    async def test_date_filter_uses_device_timezone_boundaries(self):
        db = SimpleNamespace(execute=AsyncMock(return_value=Result([])))

        await get_tasks_for_date(
            db,
            "user-id",
            date(2026, 3, 1),
            timezone_name="Pacific/Kiritimati",
        )

        params = db.execute.await_args.args[0].compile().params
        boundaries = [
            value for value in params.values()
            if isinstance(value, datetime) and value.tzinfo is not None
        ]
        self.assertIn(datetime(2026, 2, 28, 10, 0, tzinfo=timezone.utc), boundaries)
        self.assertIn(datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc), boundaries)

    async def test_activity_updates_stale_timezone_without_advancing_streak(self):
        zone = ZoneInfo("Asia/Kolkata")
        user = SimpleNamespace(
            id="user-id",
            last_active_date=datetime.now(zone).date(),
            last_active_timezone="Asia/Kolkata",
            current_streak=4,
            longest_streak=8,
        )
        db = SimpleNamespace(
            execute=AsyncMock(return_value=Result(user)),
            commit=AsyncMock(),
            refresh=AsyncMock(),
        )

        result = await record_daily_activity(db, user.id, "Asia/Kathmandu")

        self.assertEqual(result["timezone"], "Asia/Kathmandu")
        self.assertEqual(user.current_streak, 4)
        self.assertEqual(user.longest_streak, 8)
        db.commit.assert_awaited_once()
        db.refresh.assert_awaited_once_with(user)


if __name__ == "__main__":
    unittest.main()
