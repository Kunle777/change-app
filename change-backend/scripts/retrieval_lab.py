import asyncio
import sys
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

from app.database import AsyncSessionLocal  # noqa: E402
from app.memory.embedding import embed_texts  # noqa: E402
from app.memory.retrieval import (CANDIDATES_K, MIN_SIMILARITY, RetrievalResult,  # noqa: E402
                                  build_search_query, memory_prompt_section,
                                  select_memories, should_retrieve)
from app.memory.service import search_by_vector  # noqa: E402
from app.memory.time_parse import parse_time_window  # noqa: E402

USER_ID = uuid.UUID(sys.argv[1])
QUESTION = sys.argv[2]
INTENT = sys.argv[3] if len(sys.argv) > 3 else None
TZ = "Africa/Lagos"


async def main():
    now = datetime.now(timezone.utc)
    print(f"1. GATE   retrieve? {should_retrieve(QUESTION, INTENT)}")
    window = parse_time_window(QUESTION, now=now, tz_name=TZ)
    print(f"2. WINDOW {window}")
    query = build_search_query(QUESTION)
    [qvec] = await embed_texts([query], task_type="RETRIEVAL_QUERY")

    async with AsyncSessionLocal() as db:
        hits = await search_by_vector(db, user_id=USER_ID, vector=qvec, k=10,
                                      since=window.since if window else None,
                                      until=window.until if window else None)
    print(f"3. RAW TOP {len(hits)}  (threshold {MIN_SIMILARITY}, candidates used {CANDIDATES_K})")
    for h in hits:
        print(f"   {h['similarity']:.3f}  {h['source_type']:<10} {h['content'][:80]!r}")

    kept = select_memories(hits[:CANDIDATES_K])
    print(f"4. KEPT   {len(kept)}")
    print("5. PROMPT SECTION")
    print(memory_prompt_section(RetrievalResult(True, kept, window), tz_name=TZ, now=now))


asyncio.run(main())