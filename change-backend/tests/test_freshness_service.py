import os
import unittest
import uuid
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from zoneinfo import ZoneInfo

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://test:test@127.0.0.1:5432/change_app_test",
)

from app.ai import freshness_service
from app.ai.freshness_service import DataFreshness, FreshnessTier
from app.ai.prompt_builder import build_system_prompt_for_user


class FreshnessServiceTests(unittest.IsolatedAsyncioTestCase):
    def test_age_uses_local_calendar_date_not_elapsed_24_hour_periods(self):
        user_timezone = ZoneInfo("America/Los_Angeles")
        recent_activity = datetime(2026, 10, 14, 6, 30, tzinfo=timezone.utc)

        days_since = freshness_service._days_since(
            recent_activity,
            user_timezone,
            date(2026, 10, 14),
        )

        self.assertEqual(days_since, 1)

    async def test_task_activity_includes_events_outbox_and_task_timestamps(self):
        now = datetime.now(timezone.utc)
        results = [
            SimpleNamespace(scalar_one_or_none=Mock(return_value=now)),
            SimpleNamespace(scalar_one_or_none=Mock(return_value=None)),
            SimpleNamespace(scalar_one_or_none=Mock(return_value=None)),
        ]
        db = SimpleNamespace(execute=AsyncMock(side_effect=results))

        freshness = await freshness_service.compute_data_freshness(
            db,
            uuid.uuid4(),
            "Africa/Lagos",
        )

        task_query = str(db.execute.await_args_list[0].args[0]).lower()
        self.assertIn("task_events", task_query)
        self.assertIn("task_event_outbox", task_query)
        self.assertIn("tasks.created_at", task_query)
        self.assertIn("tasks.completed_at", task_query)
        self.assertIn("tasks.deleted_at", task_query)
        self.assertEqual(freshness.days_since_task_activity, 0)
        self.assertEqual(freshness.tier, FreshnessTier.FRESH)

    async def test_uses_stored_timezone_when_no_timezone_is_passed(self):
        db = SimpleNamespace(
            execute=AsyncMock(
                return_value=SimpleNamespace(
                    scalar_one_or_none=Mock(return_value="America/Los_Angeles")
                )
            )
        )

        user_timezone = await freshness_service.resolve_user_timezone(db, uuid.uuid4())

        self.assertEqual(user_timezone.key, "America/Los_Angeles")

    async def test_invalid_timezone_falls_back_to_lagos(self):
        db = SimpleNamespace(
            execute=AsyncMock(
                return_value=SimpleNamespace(
                    scalar_one_or_none=Mock(return_value="Invalid/Timezone")
                )
            )
        )

        user_timezone = await freshness_service.resolve_user_timezone(
            db,
            uuid.uuid4(),
            "Invalid/Timezone",
        )

        self.assertEqual(user_timezone.key, "Africa/Lagos")

    async def test_shared_user_prompt_includes_freshness_and_local_date(self):
        db = SimpleNamespace()
        freshness = DataFreshness(0, 3, None, FreshnessTier.AGING)
        user_timezone = ZoneInfo("America/Los_Angeles")

        with patch(
            "app.ai.prompt_builder.resolve_user_timezone",
            new=AsyncMock(return_value=user_timezone),
        ), patch(
            "app.ai.prompt_builder.compute_data_freshness",
            new=AsyncMock(return_value=freshness),
        ):
            prompt, actual_freshness = await build_system_prompt_for_user(
                db,
                uuid.uuid4(),
                "daily_review",
                "Recent check-in: mood 4/5",
                additional_instructions="Keep the summary to two sentences.",
            )

        self.assertIs(actual_freshness, freshness)
        self.assertIn(
            f"The user's local date is {datetime.now(user_timezone).date().isoformat()}",
            prompt,
        )
        self.assertIn("tasks: today", prompt)
        self.assertIn("check-ins: 3 days ago", prompt)
        self.assertIn("Keep the summary to two sentences.", prompt)


if __name__ == "__main__":
    unittest.main()
