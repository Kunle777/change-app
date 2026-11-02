import os
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://test:test@127.0.0.1:5432/change_app_test",
)

from app.ai.behavior import (  # noqa: E402
    BEHAVIOR_GUIDANCE,
    Observation,
    drop_recently_mentioned,
    load_behavior_observations,
    render_observations,
)
from app.ai.prompt_builder import SYSTEM_PROMPT  # noqa: E402
from app.tasks.models import StatusEnum  # noqa: E402

NOW = datetime(2026, 10, 20, tzinfo=timezone.utc)


class Result:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows

    def scalars(self):
        return self


def event(task_id, kind, days_ago):
    return SimpleNamespace(
        task_id=task_id, event_type=kind, occurred_at=NOW - timedelta(days=days_ago), event_metadata={}
    )


class GuidanceTests(unittest.TestCase):
    def test_prompt_tells_model_to_be_gentle_and_not_diagnose(self):
        text = BEHAVIOR_GUIDANCE.lower()
        for phrase in ("at most one", "do not recite counts", "never explain why", "condition"):
            self.assertIn(phrase, text)
        self.assertIn("sparingly", SYSTEM_PROMPT)

    def test_rendered_block_carries_the_guidance(self):
        prompt = render_observations([Observation('Observed: "Portfolio" has 3 recorded postponements.', "Portfolio")])
        self.assertIn("Observed:", prompt)
        self.assertIn(BEHAVIOR_GUIDANCE, prompt)
        self.assertEqual(render_observations([]), "")

    def test_task_already_discussed_is_not_raised_again(self):
        items = [Observation("a", "Portfolio"), Observation("b", "Rent"), Observation("c", "")]
        kept = drop_recently_mentioned(items, ["It looks like the portfolio keeps moving; want to shrink it?"])
        self.assertEqual([i.text for i in kept], ["b", "c"])
        self.assertEqual(len(drop_recently_mentioned(items, [])), 3)


class LoaderTests(unittest.IsolatedAsyncioTestCase):
    async def test_thresholds_produce_observation_with_subject(self):
        task_id = uuid.uuid4()
        rows = [event(task_id, "not_now", d) for d in (1, 2, 3)]
        db = SimpleNamespace(
            execute=AsyncMock(
                side_effect=[
                    Result(rows),
                    Result([]),
                    Result([]),
                    Result([SimpleNamespace(id=task_id, title="Portfolio")]),
                ]
            )
        )
        facts = await load_behavior_observations(db, uuid.uuid4(), needed=True, now=NOW)
        self.assertEqual(facts.state, "found")
        self.assertEqual(facts.observations[0].subject, "Portfolio")
        self.assertIn("3 recorded postponements", facts.prompt)

    async def test_below_threshold_makes_no_claim(self):
        task_id = uuid.uuid4()
        db = SimpleNamespace(
            execute=AsyncMock(
                side_effect=[
                    Result([event(task_id, "not_now", 1), event(task_id, "not_now", 2)]),
                    Result([]),
                    Result([]),
                    Result([SimpleNamespace(id=task_id, title="Portfolio")]),
                ]
            )
        )
        facts = await load_behavior_observations(db, uuid.uuid4(), needed=True, now=NOW)
        self.assertEqual(facts.state, "none_found")
        self.assertIn("Do not invent", facts.prompt)
        self.assertFalse(facts.observations)

    async def test_no_events_is_not_evidence_of_inactivity(self):
        db = SimpleNamespace(execute=AsyncMock(side_effect=[Result([]), Result([]), Result([])]))
        facts = await load_behavior_observations(db, uuid.uuid4(), needed=True, now=NOW)
        self.assertEqual(facts.state, "none_found")
        self.assertIn("not evidence", facts.prompt)

    async def test_checkin_history_is_separate_from_task_event_patterns(self):
        checkin = SimpleNamespace(
            created_at=NOW - timedelta(days=2),
            type=SimpleNamespace(value="morning"),
            mood=2,
            goal_today=None,
            reflection=None,
        )
        db = SimpleNamespace(
            execute=AsyncMock(
                side_effect=[Result([]), Result([]), Result([checkin])]
            )
        )
        facts = await load_behavior_observations(db, uuid.uuid4(), needed=True, now=NOW)
        self.assertEqual(facts.state, "found")
        self.assertIn("mood 2/5", facts.prompt)
        self.assertIn("none meet the minimum evidence threshold", facts.prompt)

    async def test_checkin_reflections_and_repeated_postponements_show_timing_overlap(self):
        task_id = uuid.uuid4()
        days = (1, 3)
        rows = [event(task_id, "not_now", day) for day in days]
        checkins = [
            SimpleNamespace(
                created_at=NOW - timedelta(days=day),
                type=SimpleNamespace(value="evening"),
                mood=3,
                goal_today=None,
                reflection="I felt overwhelmed by the amount to do",
            )
            for day in days
        ]
        db = SimpleNamespace(
            execute=AsyncMock(
                side_effect=[
                    Result(rows),
                    Result([]),
                    Result(checkins),
                    Result([SimpleNamespace(id=task_id, title="Portfolio")]),
                ]
            )
        )

        facts = await load_behavior_observations(db, uuid.uuid4(), needed=True, now=NOW)

        self.assertIn("reflection:", facts.prompt)
        self.assertIn("overwhelmed", facts.prompt)
        self.assertTrue(any("timing overlap only" in item.text for item in facts.observations))

    async def test_analysis_uses_checkins_older_than_the_prompt_display_limit(self):
        task_id = uuid.uuid4()
        dates_ago = [24, 21]
        rows = [event(task_id, "not_now", day) for day in dates_ago]
        checkins = [
            SimpleNamespace(
                created_at=NOW - timedelta(days=day),
                type=SimpleNamespace(value="evening"),
                mood=3,
                goal_today=None,
                reflection=("I felt overwhelmed" if day in dates_ago else "An ordinary day"),
            )
            for day in range(24, 0, -1)
        ]
        db = SimpleNamespace(
            execute=AsyncMock(
                side_effect=[
                    Result(rows),
                    Result([]),
                    Result(checkins),
                    Result([SimpleNamespace(id=task_id, title="Portfolio")]),
                ]
            )
        )

        facts = await load_behavior_observations(db, uuid.uuid4(), needed=True, now=NOW)

        checkin_query = db.execute.await_args_list[2].args[0]
        self.assertIn("LIMIT", str(checkin_query).upper())
        self.assertTrue(any("timing overlap only" in item.text for item in facts.observations))
        self.assertLessEqual(facts.prompt.count("evening):"), 10)

    async def test_late_completions_are_compared_only_with_known_deadlines(self):
        tasks = []
        for days_ago, late in ((1, True), (2, False), (3, True), (8, True), (9, False), (10, True)):
            completed_at = NOW - timedelta(days=days_ago)
            tasks.append(SimpleNamespace(
                status=StatusEnum.completed,
                completed_at=completed_at,
                due_date=completed_at - timedelta(hours=1) if late else completed_at + timedelta(hours=1),
                due_date_is_all_day=False,
                created_at=NOW - timedelta(days=20),
            ))
        db = SimpleNamespace(
            execute=AsyncMock(side_effect=[Result([]), Result(tasks), Result([])])
        )

        facts = await load_behavior_observations(db, uuid.uuid4(), needed=True, now=NOW)

        self.assertTrue(any("completed late in the last 7 days" in item.text for item in facts.observations))
        self.assertTrue(any("compared with 2 of 3" in item.text for item in facts.observations))

    async def test_one_missed_deadline_is_not_described_as_a_pattern(self):
        task_id = uuid.uuid4()
        db = SimpleNamespace(
            execute=AsyncMock(
                side_effect=[
                    Result([event(task_id, "overdue", 1)]),
                    Result([]),
                    Result([]),
                    Result([SimpleNamespace(id=task_id, title="Portfolio")]),
                ]
            )
        )

        facts = await load_behavior_observations(db, uuid.uuid4(), needed=True, now=NOW)

        self.assertFalse(any("overdue transitions" in item.text for item in facts.observations))
        self.assertIn("none meet the minimum evidence threshold", facts.prompt)

    async def test_cancellations_are_not_counted_as_postponements(self):
        task_id = uuid.uuid4()
        rows = [event(task_id, "cancelled", day) for day in (1, 2, 3)]
        db = SimpleNamespace(
            execute=AsyncMock(
                side_effect=[
                    Result(rows),
                    Result([]),
                    Result([]),
                    Result([SimpleNamespace(id=task_id, title="Portfolio")]),
                ]
            )
        )

        facts = await load_behavior_observations(db, uuid.uuid4(), needed=True, now=NOW)

        self.assertTrue(any("cancellations were recorded" in item.text for item in facts.observations))
        self.assertFalse(any("postponements" in item.text for item in facts.observations))


if __name__ == "__main__":
    unittest.main()
