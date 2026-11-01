import os
import unittest
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://test:test@127.0.0.1:5432/change_app_test",
)

from app.ai.task_context import load_open_task_titles, load_task_facts  # noqa: E402
from app.memory import policy, retrieval  # noqa: E402
from app.memory.policy import MemoryAccess  # noqa: E402

USER = uuid.uuid4()
NOW = datetime(2026, 10, 15, 6, 30, tzinfo=timezone.utc)


class CapturingDB:
    """Records every statement so tests can check user scoping without a database."""

    def __init__(self):
        self.statements = []
        self.nested = None
        self.rowcount = 0

        class Result:
            def scalars(self_inner):
                return self_inner

            def all(self_inner):
                return []

            def scalar_one_or_none(self_inner):
                return None

            rowcount = 3

        self._result = Result

    async def execute(self, statement, params=None):
        self.statements.append((statement, params))
        return self._result()

    def begin_nested(self):
        class Ctx:
            async def __aenter__(self_inner):
                return None

            async def __aexit__(self_inner, *a):
                return False

        return Ctx()

    async def commit(self):
        pass


def bound_values(statement):
    try:
        return list(statement.compile().params.values())
    except Exception:
        return []


class RetrievalPrivacyTests(unittest.IsolatedAsyncioTestCase):
    async def test_memory_off_blocks_before_any_embedding_or_search(self):
        with patch.object(retrieval, "memory_access", AsyncMock(return_value=MemoryAccess(False, "memory_off"))), \
             patch.object(retrieval, "embed_texts", AsyncMock()) as embed, \
             patch.object(retrieval, "search_by_vector", AsyncMock()) as search:
            result = await retrieval.retrieve_memories(
                CapturingDB(), user_id=USER, question="what did I write last week?", intent="recall", needed=True
            )
        self.assertEqual(result.state, "blocked")
        self.assertFalse(result.memories)
        embed.assert_not_awaited()
        search.assert_not_awaited()
        self.assertIn("turned off", retrieval.memory_prompt_section(result))

    async def test_ai_disabled_account_is_blocked_too(self):
        with patch.object(retrieval, "memory_access", AsyncMock(return_value=MemoryAccess(False, "ai_disabled"))):
            result = await retrieval.retrieve_memories(
                CapturingDB(), user_id=USER, question="remember when I said", intent="recall", needed=True
            )
        self.assertEqual(result.state, "blocked")

    async def test_search_is_scoped_to_the_authenticated_user_and_excludes_history(self):
        search = AsyncMock(return_value=[
            {"similarity": 0.9, "source_id": "in-history", "source_type": "conversation_user",
             "content": "already in this chat", "source_created_at": NOW},
            {"similarity": 0.85, "source_id": "other", "source_type": "brain_dump",
             "content": "older entry", "source_created_at": NOW},
        ])
        with patch.object(retrieval, "memory_access", AsyncMock(return_value=MemoryAccess(True, "ok"))), \
             patch.object(retrieval, "embed_texts", AsyncMock(return_value=[[0.0] * 3])), \
             patch.object(retrieval, "search_by_vector", search):
            result = await retrieval.retrieve_memories(
                CapturingDB(), user_id=USER, question="what did I say about my goals", intent="recall",
                needed=True, exclude_source_ids=["in-history"],
            )
        self.assertEqual(search.await_args.kwargs["user_id"], USER)
        self.assertEqual([m.source_id for m in result.memories], ["other"])


class TaskScopingTests(unittest.IsolatedAsyncioTestCase):
    async def test_every_task_query_is_filtered_by_user(self):
        db = CapturingDB()
        await load_task_facts(db, USER, need_tasks=True, need_events=True, timezone_name="Africa/Lagos", now=NOW)
        await load_open_task_titles(db, USER)
        self.assertGreaterEqual(len(db.statements), 5)
        for statement, _ in db.statements:
            self.assertIn(USER, bound_values(statement), str(statement)[:120])


class OptOutTests(unittest.IsolatedAsyncioTestCase):
    async def test_turning_memory_off_deletes_only_derived_chunks(self):
        db = CapturingDB()
        result = await policy.set_personal_memory(db, USER, False)
        sql = " ".join(str(statement) for statement, _ in db.statements).lower()
        self.assertIn("delete from memory_chunks", sql)
        for original in ("brain_dumps", "check_ins", "ai_interactions", "tasks"):
            self.assertNotIn(f"delete from {original}", sql)
        self.assertFalse(result["enabled"])

    async def test_turning_memory_on_purges_nothing(self):
        db = CapturingDB()
        await policy.set_personal_memory(db, USER, True)
        self.assertNotIn("delete from", " ".join(str(s) for s, _ in db.statements).lower())


if __name__ == "__main__":
    unittest.main()
