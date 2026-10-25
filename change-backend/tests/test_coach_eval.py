import os
import unittest

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://test:test@127.0.0.1:5432/change_app_test",
)

from eval.coach_cases import CASES  # noqa: E402
from eval.coach_harness import run_scenario  # noqa: E402


class CoachEvalTests(unittest.IsolatedAsyncioTestCase):
    async def test_all_cases(self):
        for case in CASES:
            with self.subTest(group=case["group"], case=case["name"]):
                context, mocks = await run_scenario(case["scenario"])
                prompt = context.system_prompt
                for text in case.get("must_contain", []):
                    self.assertIn(text, prompt)
                for text in case.get("must_not_contain", []):
                    self.assertNotIn(text, prompt)
                offer, confirm = case["tools"]
                self.assertEqual(context.allow_tools, offer)
                self.assertEqual(context.require_confirmation, confirm)
                if "history_len" in case:
                    self.assertEqual(len(context.history), case["history_len"])
                if "previous_question" in case:
                    kwargs = mocks.retrieve.await_args.kwargs
                    self.assertEqual(kwargs["previous_question"], case["previous_question"])

    def test_every_required_group_is_covered(self):
        groups = {case["group"] for case in CASES}
        self.assertEqual(
            groups,
            {"multi_source", "continuity", "task_action_with_memory", "unsupported_claims"},
        )


if __name__ == "__main__":
    unittest.main()
