import os
import math
import unittest
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://test:test@127.0.0.1:5432/change_app_test",
)

from app.braindump import service as braindump_service
from app.memory import embedding, service
from app.memory.config import EMBEDDING_DIM


class MemoryEmbeddingTests(unittest.IsolatedAsyncioTestCase):
    async def test_empty_input_does_not_call_gemini(self):
        with patch.object(embedding, "get_client") as get_client:
            self.assertEqual(await embedding.embed_texts([], task_type="RETRIEVAL_QUERY"), [])
        get_client.assert_not_called()

    async def test_normalizes_vectors_and_uses_requested_task(self):
        values = [3.0] + [0.0] * (EMBEDDING_DIM - 1)
        embed_content = AsyncMock(
            side_effect=[
                SimpleNamespace(embeddings=[SimpleNamespace(values=values)]),
                SimpleNamespace(embeddings=[SimpleNamespace(values=values)]),
            ]
        )
        client = SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(embed_content=embed_content)))

        with patch.object(embedding, "get_client", return_value=client):
            vectors = await embedding.embed_texts(
                ["a search query", "another query"], task_type="RETRIEVAL_QUERY"
            )

        self.assertEqual(len(vectors), 2)
        self.assertEqual(len(vectors[0]), EMBEDDING_DIM)
        self.assertTrue(math.isclose(math.sqrt(sum(value * value for value in vectors[0])), 1))
        self.assertEqual(embed_content.await_count, 2)
        self.assertEqual(
            [call.kwargs["contents"] for call in embed_content.await_args_list],
            ["a search query", "another query"],
        )
        self.assertEqual(
            embed_content.await_args.kwargs["config"].task_type,
            "RETRIEVAL_QUERY",
        )

    async def test_rejects_wrong_embedding_dimension(self):
        client = SimpleNamespace(
            aio=SimpleNamespace(
                models=SimpleNamespace(
                    embed_content=AsyncMock(
                        return_value=SimpleNamespace(
                            embeddings=[SimpleNamespace(values=[1.0])]
                        )
                    )
                )
            )
        )
        with patch.object(embedding, "get_client", return_value=client):
            with self.assertRaisesRegex(ValueError, "dimension mismatch"):
                await embedding.embed_texts(["text"], task_type="RETRIEVAL_DOCUMENT")


class MemoryServiceTests(unittest.IsolatedAsyncioTestCase):
    def test_hash_and_pgvector_serialization(self):
        self.assertEqual(
            service.content_hash("hello"),
            "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
        )
        self.assertEqual(service.to_pgvector([0.25, -0.5]), "[0.25,-0.5]")

    async def test_store_chunk_embeds_and_leaves_commit_to_caller(self):
        db = SimpleNamespace(execute=AsyncMock(return_value=SimpleNamespace(rowcount=1)))
        user_id = uuid.uuid4()
        source_id = uuid.uuid4()
        created_at = datetime.now(timezone.utc)

        with patch.object(service, "embed_texts", new=AsyncMock(return_value=[[0.5] * EMBEDDING_DIM])) as embed:
            await service.store_chunk(
                db,
                user_id=user_id,
                source_type="brain_dump",
                source_id=source_id,
                chunk_index=0,
                content="private test text",
                source_created_at=created_at,
            )

        embed.assert_awaited_once_with(
            ["private test text"], task_type="RETRIEVAL_DOCUMENT"
        )
        db.execute.assert_awaited_once()
        self.assertEqual(db.execute.await_args.args[1]["user_id"], user_id)
        self.assertEqual(db.execute.await_args.args[1]["source_id"], source_id)

    async def test_search_is_user_and_model_scoped_and_applies_optional_filters(self):
        row = {"content": "result", "similarity": 0.9}
        mappings = Mock()
        mappings.all.return_value = [row]
        result = Mock(mappings=Mock(return_value=mappings))
        db = SimpleNamespace(execute=AsyncMock(return_value=result))
        user_id = uuid.uuid4()
        since = datetime.now(timezone.utc)

        with patch.object(service, "embed_texts", new=AsyncMock(return_value=[[0.0] * EMBEDDING_DIM])):
            hits = await service.search_chunks(
                db,
                user_id=user_id,
                query="find this",
                source_types=["brain_dump"],
                since=since,
            )

        self.assertEqual(hits, [row])
        statement = str(db.execute.await_args.args[0])
        params = db.execute.await_args.args[1]
        self.assertIn("user_id = :user_id", statement)
        self.assertIn("embedding_model = :model", statement)
        self.assertIn("source_type = ANY", statement)
        self.assertIn("source_created_at >= :since", statement)
        self.assertEqual(params["user_id"], user_id)
        self.assertEqual(params["source_types"], ["brain_dump"])
        self.assertEqual(params["since"], since)

    async def test_search_rejects_invalid_result_limit(self):
        db = SimpleNamespace(execute=AsyncMock())
        with self.assertRaisesRegex(ValueError, "k must be between"):
            await service.search_chunks(db, user_id=uuid.uuid4(), query="text", k=0)
        db.execute.assert_not_awaited()

    async def test_deleting_brain_dump_deletes_its_chunks_first(self):
        user_id = uuid.uuid4()
        dump_id = uuid.uuid4()
        dump = SimpleNamespace(id=dump_id)
        db = SimpleNamespace(
            execute=AsyncMock(),
            delete=AsyncMock(),
            commit=AsyncMock(),
        )

        with patch.object(
            braindump_service,
            "get_brain_dump_by_id",
            new=AsyncMock(return_value=dump),
        ):
            deleted = await braindump_service.delete_brain_dump(db, dump_id, user_id)

        self.assertIs(deleted, dump)
        db.execute.assert_awaited_once()
        delete_query = str(db.execute.await_args.args[0])
        self.assertIn("user_id = :user_id", delete_query)
        self.assertIn("source_type = :source_type", delete_query)
        self.assertIn("source_id = :source_id", delete_query)
        db.delete.assert_awaited_once_with(dump)
        db.commit.assert_awaited_once()
