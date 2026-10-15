import asyncio
import os
import unittest
import uuid
from unittest.mock import AsyncMock, patch

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


TEST_DATABASE_URL = os.getenv("MEMORY_TEST_DATABASE_URL")
if TEST_DATABASE_URL:
    parsed_test_url = make_url(TEST_DATABASE_URL)
    if parsed_test_url.drivername in {"postgres", "postgresql"}:
        parsed_test_url = parsed_test_url.set(drivername="postgresql+asyncpg")
    TEST_DATABASE_URL = parsed_test_url.render_as_string(hide_password=False)
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
TEST_DATABASE_NAME = (
    make_url(TEST_DATABASE_URL).database if TEST_DATABASE_URL else None
)
EMBEDDING = [1.0] + [0.0] * 767


@unittest.skipUnless(
    TEST_DATABASE_URL,
    "Set MEMORY_TEST_DATABASE_URL to a disposable, migrated PostgreSQL test database",
)
class MemoryPostgresIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        if not TEST_DATABASE_NAME or "test" not in TEST_DATABASE_NAME.lower():
            self.fail(
                "MEMORY_TEST_DATABASE_URL must target a database whose name contains 'test'"
            )

        self.engine = create_async_engine(
            TEST_DATABASE_URL,
            connect_args={"statement_cache_size": 0},
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.user_id = uuid.uuid4()
        self.source_id = uuid.uuid4()

        async with self.engine.begin() as conn:
            database_name = await conn.scalar(text("SELECT current_database()"))
            if "test" not in database_name.lower():
                self.fail("Refusing to write to a database not named as a test database")
            await conn.execute(
                text("INSERT INTO users (id) VALUES (:id)"),
                {"id": self.user_id},
            )
            await conn.execute(
                text(
                    "INSERT INTO feature_entitlements "
                    "(id, user_id, ai_enabled, brain_dump_enabled, premium) "
                    "VALUES (:id, :user_id, true, true, false)"
                ),
                {"id": uuid.uuid4(), "user_id": self.user_id},
            )

    async def asyncTearDown(self):
        if not hasattr(self, "engine"):
            return
        async with self.engine.begin() as conn:
            await conn.execute(
                text("DELETE FROM memory_chunks WHERE user_id = :user_id"),
                {"user_id": self.user_id},
            )
            await conn.execute(
                text("DELETE FROM checkins WHERE id = :source_id"),
                {"source_id": self.source_id},
            )
            await conn.execute(
                text("DELETE FROM brain_dumps WHERE id = :source_id"),
                {"source_id": self.source_id},
            )
            await conn.execute(
                text("DELETE FROM users WHERE id = :user_id"),
                {"user_id": self.user_id},
            )
        await self.engine.dispose()

    async def add_brain_dump(self, content: str) -> None:
        async with self.engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO brain_dumps (id, user_id, content) "
                    "VALUES (:id, :user_id, :content)"
                ),
                {
                    "id": self.source_id,
                    "user_id": self.user_id,
                    "content": content,
                },
            )

    async def add_checkin(self, goal: str, reflection: str, ai_summary: str) -> None:
        async with self.engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO checkins "
                    "(id, user_id, type, goal_today, reflection, ai_summary) "
                    "VALUES (:id, :user_id, 'evening', :goal, :reflection, :summary)"
                ),
                {
                    "id": self.source_id,
                    "user_id": self.user_id,
                    "goal": goal,
                    "reflection": reflection,
                    "summary": ai_summary,
                },
            )

    async def index(self, source_type: str = "brain_dump") -> int:
        from app.memory.indexer import index_source

        async with self.sessions() as db:
            return await index_source(
                db,
                source_type=source_type,
                source_id=self.source_id,
                user_id=self.user_id,
            )

    async def memory_rows(self) -> list[dict]:
        async with self.engine.connect() as conn:
            rows = (
                await conn.execute(
                    text(
                        "SELECT content, content_hash, embedding_dim "
                        "FROM memory_chunks WHERE user_id = :user_id "
                        "AND source_id = :source_id ORDER BY chunk_index"
                    ),
                    {"user_id": self.user_id, "source_id": self.source_id},
                )
            ).mappings()
            return [dict(row) for row in rows]

    async def test_concurrent_indexing_keeps_one_correct_chunk(self):
        from app.memory import indexer

        await self.add_brain_dump("One concurrent source")
        both_embedding_calls_started = asyncio.Event()
        release_embeddings = asyncio.Event()
        call_count = 0

        async def mock_embedding(contents, *, task_type):
            nonlocal call_count
            self.assertEqual(contents, ["One concurrent source"])
            self.assertEqual(task_type, "RETRIEVAL_DOCUMENT")
            call_count += 1
            if call_count == 2:
                both_embedding_calls_started.set()
            await release_embeddings.wait()
            return [EMBEDDING]

        with patch.object(indexer, "embed_texts", side_effect=mock_embedding):
            indexing = [
                asyncio.create_task(self.index()),
                asyncio.create_task(self.index()),
            ]
            try:
                await asyncio.wait_for(both_embedding_calls_started.wait(), timeout=10)
            finally:
                release_embeddings.set()
            counts = await asyncio.gather(*indexing)

        self.assertEqual(call_count, 2)
        self.assertEqual(sum(counts), 2)
        rows = await self.memory_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["content"], "One concurrent source")
        self.assertEqual(rows[0]["embedding_dim"], 768)

    async def test_delete_during_embedding_does_not_resurrect_chunks(self):
        from app.memory import indexer

        await self.add_brain_dump("Delete while the embedding request is in flight")
        embedding_started = asyncio.Event()
        release_embedding = asyncio.Event()

        async def mock_embedding(contents, *, task_type):
            self.assertEqual(task_type, "RETRIEVAL_DOCUMENT")
            embedding_started.set()
            await release_embedding.wait()
            return [EMBEDDING]

        with patch.object(indexer, "embed_texts", side_effect=mock_embedding):
            async with self.sessions() as db:
                indexing = asyncio.create_task(
                    indexer.index_source(
                        db,
                        source_type="brain_dump",
                        source_id=self.source_id,
                        user_id=self.user_id,
                    )
                )
                await asyncio.wait_for(embedding_started.wait(), timeout=10)
                async with self.engine.begin() as conn:
                    await conn.execute(
                        text("DELETE FROM brain_dumps WHERE id = :source_id"),
                        {"source_id": self.source_id},
                    )
                release_embedding.set()
                await indexing

        rows = await self.memory_rows()
        self.assertEqual(rows, [])
        async with self.engine.connect() as conn:
            source_exists = await conn.scalar(
                text("SELECT EXISTS (SELECT 1 FROM brain_dumps WHERE id = :id)"),
                {"id": self.source_id},
            )
        self.assertFalse(source_exists)

    async def test_edited_checkin_is_reconciled_without_ai_summary(self):
        from app.memory import indexer

        await self.add_checkin(
            "Old goal",
            "Old reflection",
            "This AI-generated summary must never be indexed",
        )
        embedding_started = asyncio.Event()
        release_first_embedding = asyncio.Event()
        embedding_inputs: list[list[str]] = []

        async def mock_embedding(contents, *, task_type):
            self.assertEqual(task_type, "RETRIEVAL_DOCUMENT")
            embedding_inputs.append(contents)
            if len(embedding_inputs) == 1:
                embedding_started.set()
                await release_first_embedding.wait()
            return [EMBEDDING for _ in contents]

        with patch.object(indexer, "embed_texts", side_effect=mock_embedding):
            async with self.sessions() as db:
                initial_index = asyncio.create_task(
                    indexer.index_source(
                        db,
                        source_type="check_in",
                        source_id=self.source_id,
                        user_id=self.user_id,
                    )
                )
                await asyncio.wait_for(embedding_started.wait(), timeout=10)
                async with self.engine.begin() as conn:
                    await conn.execute(
                        text(
                            "UPDATE checkins SET goal_today = :goal, "
                            "reflection = :reflection WHERE id = :source_id"
                        ),
                        {
                            "goal": "New goal",
                            "reflection": "New reflection",
                            "source_id": self.source_id,
                        },
                    )
                release_first_embedding.set()
                await initial_index

            await self.index(source_type="check_in")

        rows = await self.memory_rows()
        self.assertTrue(rows)
        indexed_text = "\n".join(row["content"] for row in rows)
        self.assertIn("New goal", indexed_text)
        self.assertIn("New reflection", indexed_text)
        self.assertNotIn("Old goal", indexed_text)
        self.assertNotIn("Old reflection", indexed_text)
        self.assertNotIn("AI-generated summary", indexed_text)
        self.assertGreaterEqual(len(embedding_inputs), 2)

    async def test_ai_opt_out_purges_existing_and_blocks_new_chunks(self):
        from app.memory import indexer

        await self.add_brain_dump("User opted out")
        with patch.object(
            indexer,
            "embed_texts",
            new=AsyncMock(return_value=[EMBEDDING]),
        ):
            await self.index()
            self.assertEqual(len(await self.memory_rows()), 1)

            async with self.engine.begin() as conn:
                await conn.execute(
                    text(
                        "UPDATE feature_entitlements SET ai_enabled = false "
                        "WHERE user_id = :user_id"
                    ),
                    {"user_id": self.user_id},
                )
            self.assertEqual(await self.memory_rows(), [])
            await self.index()
            self.assertEqual(await self.memory_rows(), [])


if __name__ == "__main__":
    unittest.main()
