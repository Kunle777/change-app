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
                    Result([SimpleNamespace(id=task_id, title="Portfolio")]),
                ]
            )
        )
        facts = await load_behavior_observations(db, uuid.uuid4(), needed=True, now=NOW)
        self.assertEqual(facts.state, "none_found")
        self.assertIn("Do not invent", facts.prompt)
        self.assertFalse(facts.observations)

    async def test_no_events_is_not_evidence_of_inactivity(self):
        db = SimpleNamespace(execute=AsyncMock(side_effect=[Result([]), Result([])]))
        facts = await load_behavior_observations(db, uuid.uuid4(), needed=True, now=NOW)
        self.assertEqual(facts.state, "none_found")
        self.assertIn("not evidence", facts.prompt)


if __name__ == "__main__":
    unittest.main()
