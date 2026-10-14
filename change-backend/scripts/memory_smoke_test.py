"""Exercise memory storage and search, then remove all inserted chunks."""

import asyncio
import sys
import uuid
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import text  # noqa: E402

from app.database import AsyncSessionLocal  # noqa: E402
from app.memory.service import search_chunks, store_chunk  # noqa: E402


SAMPLES = [
    ("I keep putting off my portfolio website, starting feels overwhelming", 12),
    ("Finished the AI wrapper and submitted it", 10),
    ("Low energy today, could not focus on anything", 8),
    ("Buy milk, call mum, pay the electricity bill", 5),
    ("Great workout this morning, felt energised", 3),
    ("Idea: record a KunleTech video about RAG", 1),
]
QUERIES = ["what am I avoiding?", "errands", "when did I feel tired?"]


async def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/memory_smoke_test.py <user-uuid>")
    user_id = uuid.UUID(sys.argv[1])
    now = datetime.now(timezone.utc)
    source_ids = [uuid.uuid4() for _ in SAMPLES]
    chunks_committed = False

    async with AsyncSessionLocal() as db:
        try:
            for (content, days_ago), source_id in zip(SAMPLES, source_ids):
                await store_chunk(
                    db,
                    user_id=user_id,
                    source_type="brain_dump",
                    source_id=source_id,
                    chunk_index=0,
                    content=content,
                    source_created_at=now - timedelta(days=days_ago),
                )
            await db.commit()
            chunks_committed = True

            for query in QUERIES:
                print(f"\nQUERY: {query}")
                for hit in await search_chunks(db, user_id=user_id, query=query, k=3):
                    print(f"  {hit['similarity']:.3f}  {hit['content']}")

            print("\nLast 4 days only (metadata filter, not vectors):")
            recent = await search_chunks(
                db,
                user_id=user_id,
                query="anything",
                k=5,
                since=now - timedelta(days=4),
            )
            if len(recent) != 2:
                raise AssertionError(f"Expected 2 recent chunks, got {len(recent)}")
            for hit in recent:
                print(f"  {hit['similarity']:.3f}  {hit['content']}")

            other_user_hits = await search_chunks(
                db,
                user_id=uuid.uuid4(),
                query="what am I avoiding?",
            )
            print("\nAnother user's search returns:", other_user_hits)
            if other_user_hits:
                raise AssertionError("Search returned another user's memory chunks")
        finally:
            await db.rollback()
            deleted = await db.execute(
                text(
                    "DELETE FROM memory_chunks "
                    "WHERE user_id = :user_id AND source_id = ANY(CAST(:ids AS uuid[])) "
                    "RETURNING source_id"
                ),
                {"user_id": user_id, "ids": source_ids},
            )
            await db.commit()
            deleted_ids = {row[0] for row in deleted.all()}
            if chunks_committed and deleted_ids != set(source_ids):
                raise RuntimeError(
                    f"Smoke-test cleanup removed {len(deleted_ids)} of {len(source_ids)} chunks"
                )
            print(f"\nCleaned up {len(deleted_ids)} smoke-test chunks")


if __name__ == "__main__":
    asyncio.run(main())
