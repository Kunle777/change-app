import os
import unittest
from datetime import datetime, timedelta, timezone

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://test:test@127.0.0.1:5432/change_app_test",
)

from app.ai.behavior import BehaviorFacts  # noqa: E402
from app.ai.context_budget import Block, fit_blocks, omission_note  # noqa: E402
from app.ai.context_service import apply_context_budget  # noqa: E402
from app.ai.task_context import TaskFacts, TaskGroup, render_groups  # noqa: E402
from app.memory.retrieval import RetrievalResult, RetrievedMemory  # noqa: E402

T0 = datetime(2026, 10, 1, tzinfo=timezone.utc)


def mem(i, similarity, size=300):
    return RetrievedMemory("brain_dump", f"s{i}", f"memory-{i} " + "x" * size, T0 + timedelta(days=i), similarity)


def turns(n, size=400):
    return [{"question": f"q{i} " + "a" * size, "response": f"r{i} " + "b" * size} for i in range(n)]


class FitBlocksTests(unittest.TestCase):
    def test_under_budget_keeps_everything(self):
        result = fit_blocks([Block("a", 0, ["x" * 10]), Block("b", 1, ["y" * 10])], budget=1000)
        self.assertEqual(result.kept, {"a": 1, "b": 1})
        self.assertFalse(result.omitted)

    def test_lowest_priority_is_dropped_first_from_the_tail(self):
        a = Block("tasks", 0, ["t1" * 20, "t2" * 20, "t3" * 20])
        b = Block("memory", 4, ["m1" * 20, "m2" * 20, "m3" * 20])
        result = fit_blocks([a, b], budget=190)
        self.assertEqual(result.kept["tasks"], 3)
        self.assertLess(result.kept["memory"], 3)

    def test_min_items_are_never_trimmed(self):
        a = Block("tasks", 0, ["t" * 100] * 3, min_items=3)
        b = Block("memory", 4, ["m" * 100] * 3, min_items=1)
        result = fit_blocks([a, b], budget=50)
        self.assertEqual(result.kept, {"tasks": 3, "memory": 1})
        self.assertTrue(result.over_budget)

    def test_omission_note_names_what_was_left_out(self):
        self.assertIn("2 memory", omission_note({"memory": 2}))
        self.assertEqual(omission_note({}), "")


class AssemblyBudgetTests(unittest.TestCase):
    def test_many_memories_do_not_push_out_task_facts(self):
        groups = [
            TaskGroup("overdue", 0.0, "Overdue open tasks:", [f"- task {i} " + "t" * 150 for i in range(6)], 3),
            TaskGroup("events", 3.0, "Recorded task events:", [f"- event {i} " + "e" * 100 for i in range(6)]),
        ]
        tasks = TaskFacts("found", render_groups(groups), groups=groups)
        memories = [mem(i, 0.9 - i * 0.01, 1400) for i in range(5)]
        _, memory, tasks_prompt, _, note = apply_context_budget(
            [], RetrievalResult("found", memories, mode="vector"), tasks, BehaviorFacts("not_needed", "")
        )
        for i in range(6):
            self.assertIn(f"task {i}", tasks_prompt)
        self.assertTrue(note)
        self.assertGreaterEqual(len(memory.memories), 1)

    def test_lowest_similarity_memories_are_dropped_and_order_is_chronological(self):
        groups = [TaskGroup("overdue", 0.0, "Overdue open tasks:", ["- " + "t" * 3000 for _ in range(3)], 3)]
        tasks = TaskFacts("found", render_groups(groups), groups=groups)
        memories = [mem(1, 0.6), mem(2, 0.9), mem(3, 0.8)]
        _, memory, _, _, _ = apply_context_budget(
            [], RetrievalResult("found", memories, mode="vector"), tasks, BehaviorFacts("not_needed", "")
        )
        kept = [m.source_id for m in memory.memories]
        self.assertIn("s2", kept)
        self.assertNotIn("s1", kept)
        self.assertEqual(kept, sorted(kept))

    def test_last_two_turns_survive_but_older_ones_go_first(self):
        groups = [TaskGroup("overdue", 0.0, "Overdue open tasks:", ["- " + "t" * 5500], 1)]
        tasks = TaskFacts("found", render_groups(groups), groups=groups)
        history, _, _, _, _ = apply_context_budget(
            turns(7), RetrievalResult("not_needed"), tasks, BehaviorFacts("not_needed", "")
        )
        self.assertGreaterEqual(len(history), 2)
        self.assertLess(len(history), 7)
        self.assertTrue(history[-1]["question"].startswith("q6"))

    def test_header_only_statement_is_kept(self):
        groups = [TaskGroup("events_none", 3.0, "No recorded events in the last 30 days.", [])]
        self.assertIn("No recorded events", render_groups(groups, {"events_none": 0}))

    def test_nothing_is_cut_mid_item(self):
        groups = [TaskGroup("events", 3.0, "Events:", [f"- event {i} END" for i in range(40)])]
        tasks = TaskFacts("found", render_groups(groups), groups=groups)
        _, _, prompt, _, _ = apply_context_budget(
            [], RetrievalResult("found", [mem(1, 0.9, 6500)], mode="vector"), tasks, BehaviorFacts("not_needed", "")
        )
        for line in prompt.splitlines()[1:]:
            self.assertTrue(line.endswith("END"), line)


if __name__ == "__main__":
    unittest.main()
