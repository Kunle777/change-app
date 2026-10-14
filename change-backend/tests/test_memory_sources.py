import os
import unittest
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://test:test@127.0.0.1:5432/change_app_test",
)

from app.memory import indexer
from app.memory.config import EMBEDDING_DIM
from app.memory.sources import check_in_texts, load_source


class MemorySourceTests(unittest.IsolatedAsyncioTestCase):
    def test_checkin_text_uses_user_fields_and_mood_label(self):
        text = check_in_texts(
            kind="evening",
            mood=2,
            goal_today="Finish the draft",
            goal_status="in progress",
            reflection="I felt distracted",
        )

        self.assertEqual(
            text,
            [
                "Evening check-in. Mood: low (2/5). Goal: Finish the draft. "
                "Goal status: in progress. Reflection: I felt distracted"
            ],
        )

    def test_checkin_without_user_authored_text_is_ignored(self):
        self.assertEqual(
            check_in_texts(
                kind="morning",
                mood=2,
                goal_today=None,
                goal_status=None,
                reflection="  ",
            ),
            [],
        )

    async def test_load_source_returns_empty_text_for_existing_empty_dump(self):
        created_at = datetime.now(timezone.utc)
        dump = SimpleNamespace(content=" \n ", created_at=created_at)
        db = SimpleNamespace(
            execute=AsyncMock(
                return_value=SimpleNamespace(
                    scalar_one_or_none=Mock(return_value=dump)
                )
            )
        )

        loaded = await load_source(
            db,
            source_type="brain_dump",
            source_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
        )

        self.assertEqual(loaded, ([], created_at))

    async def test_missing_ai_entitlement_disables_embedding(self):
        db = SimpleNamespace(
            execute=AsyncMock(
                return_value=SimpleNamespace(first=Mock(return_value=None))
            ),
            commit=AsyncMock(),
        )
        self.assertFalse(await indexer.ai_allowed(db, uuid.uuid4()))

    async def test_false_ai_entitlement_disables_embedding(self):
        db = SimpleNamespace(
            execute=AsyncMock(
                return_value=SimpleNamespace(first=Mock(return_value=(False,)))
            )
        )
        user_id = uuid.uuid4()
        self.assertFalse(await indexer.ai_allowed(db, user_id))

    async def test_indexing_skips_all_external_calls_without_ai_entitlement(self):
        db = SimpleNamespace(
            execute=AsyncMock(
                return_value=SimpleNamespace(first=Mock(return_value=None))
            ),
            commit=AsyncMock(),
        )
        with patch.object(indexer, "load_source", new=AsyncMock()) as load_source_mock, patch.object(
            indexer, "embed_texts", new=AsyncMock()
        ) as embed_mock:
            count = await indexer.index_source(
                db,
                source_type="brain_dump",
                source_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
            )

        self.assertEqual(count, 0)
        load_source_mock.assert_not_awaited()
        embed_mock.assert_not_awaited()
        db.commit.assert_not_awaited()

    async def test_indexing_embeds_and_upserts_new_source_chunks(self):
        source_id = uuid.uuid4()
        user_id = uuid.uuid4()
        source_created_at = datetime.now(timezone.utc)
        db = SimpleNamespace(
            execute=AsyncMock(
                side_effect=[
                    SimpleNamespace(first=Mock(return_value=(True,))),
                    SimpleNamespace(all=Mock(return_value=[])),
                    SimpleNamespace(rowcount=1),
                    SimpleNamespace(rowcount=1),
                ]
            ),
            commit=AsyncMock(),
        )

        with patch.object(
            indexer,
            "load_source",
            new=AsyncMock(return_value=(["original user text"], source_created_at)),
        ), patch.object(
            indexer,
            "embed_texts",
            new=AsyncMock(return_value=[[0.25] * EMBEDDING_DIM]),
        ) as embed_mock, patch.object(
            indexer,
            "upsert_chunk",
            new=AsyncMock(),
        ) as upsert_mock:
            indexed_count = await indexer.index_source(
                db,
                source_type="brain_dump",
                source_id=source_id,
                user_id=user_id,
            )

        self.assertEqual(indexed_count, 1)
        embed_mock.assert_awaited_once_with(
            ["original user text"], task_type="RETRIEVAL_DOCUMENT"
        )
        upsert_mock.assert_awaited_once()
        self.assertEqual(upsert_mock.await_args.kwargs["user_id"], user_id)
        self.assertEqual(upsert_mock.await_args.kwargs["source_id"], source_id)
        self.assertEqual(upsert_mock.await_args.kwargs["content"], "original user text")
        db.commit.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
