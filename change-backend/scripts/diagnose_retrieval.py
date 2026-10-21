"""Diagnose a memory zero-hit incident without changing data.

Usage: PYTHONPATH=$PWD python scripts/diagnose_retrieval.py <user-uuid> "question" [intent]
"""
import asyncio
import sys
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import text  # noqa: E402
from app.database import AsyncSessionLocal  # noqa: E402
from app.memory.config import EMBEDDING_MODEL  # noqa: E402
from app.memory.embedding import embed_texts  # noqa: E402
from app.memory.retrieval import MIN_SIMILARITY, build_search_query, should_retrieve  # noqa: E402
from app.memory.service import search_by_vector  # noqa: E402
from app.memory.time_parse import parse_time_window  # noqa: E402

USER_ID = uuid.UUID(sys.argv[1])
QUESTION = sys.argv[2]
INTENT = sys.argv[3] if len(sys.argv) > 3 else None


async def scalar(db, sql, **params):
    return (await db.execute(text(sql), params)).scalar_one()


async def main():
    now = datetime.now(timezone.utc)
    print(f"configured model = {EMBEDDING_MODEL!r}   threshold = {MIN_SIMILARITY}")
    async with AsyncSessionLocal() as db:
        user_ok = await scalar(db, "SELECT count(*) FROM users WHERE id = :u", u=USER_ID)
        print(f"1. user row exists:         {bool(user_ok)}")
        entitlement = (await db.execute(text(
            "SELECT ai_enabled FROM feature_entitlements WHERE user_id = :u"), {"u": USER_ID}
        )).first()
        print(f"2. entitlement row:         {'MISSING' if entitlement is None else 'ai_enabled=' + str(entitlement[0])}")
        try:
            flag = await scalar(db, "SELECT personal_memory_enabled FROM users WHERE id = :u", u=USER_ID)
            print(f"3. personal_memory_enabled: {flag}")
        except Exception:
            print("3. personal_memory_enabled: column not present yet (migration not applied)")
        total = await scalar(db, "SELECT count(*) FROM memory_chunks")
        mine = await scalar(db, "SELECT count(*) FROM memory_chunks WHERE user_id = :u", u=USER_ID)
        models = (await db.execute(
            text("SELECT embedding_model, count(*) FROM memory_chunks WHERE user_id = :u GROUP BY 1"),
            {"u": USER_ID},
        )).all()
        print(f"4. chunks: table={total}  this user={mine}  by model={[(model, count) for model, count in models]}")
        window = parse_time_window(QUESTION, now=now, tz_name="Africa/Lagos")
        in_window = None
        if window:
            in_window = await scalar(
                db, "SELECT count(*) FROM memory_chunks WHERE user_id = :u "
                    "AND source_created_at >= :start AND source_created_at < :end",
                u=USER_ID, start=window.since, end=window.until or now,
            )
        print(f"5. time window: {window}   chunks inside it: {in_window}")
        print(f"6. gate: phrasing={should_retrieve(QUESTION, None)} intent={should_retrieve(QUESTION, INTENT) if INTENT else None}")
        [vector] = await embed_texts([build_search_query(QUESTION)], task_type="RETRIEVAL_QUERY")
        hits = await search_by_vector(db, user_id=USER_ID, vector=vector, k=10,
                                      since=window.since if window else None,
                                      until=window.until if window else None)
        print(f"7. raw top {len(hits)} (no threshold):")
        for hit in hits:
            print(f"     {hit['similarity']:.3f}  {hit['source_type']:<10} {hit['content'][:70]!r}")
    best = max((hit["similarity"] for hit in hits), default=None)
    if not user_ok:
        verdict = "WRONG USER ID: no matching users row"
    elif mine == 0:
        verdict = "NO CHUNKS for this user (not indexed yet, or indexing was blocked)"
    elif EMBEDDING_MODEL not in {model for model, _ in models}:
        verdict = "MODEL MISMATCH: chunks use a different embedding model"
    elif window and not in_window:
        verdict = "DATE FILTER excludes every chunk"
    elif not hits:
        verdict = "NO ROWS returned although chunks exist: investigate the SQL"
    elif best < MIN_SIMILARITY:
        verdict = f"THRESHOLD: best similarity {best:.3f} is below {MIN_SIMILARITY}"
    elif not (should_retrieve(QUESTION, None) or (INTENT and should_retrieve(QUESTION, INTENT))):
        verdict = "GATE: this phrasing would not trigger retrieval"
    else:
        verdict = "Retrieval works. Check permission handling and chat wiring."
    print("\nVERDICT:", verdict)


asyncio.run(main())
