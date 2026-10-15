import hashlib
import uuid
from datetime import datetime
from typing import Iterable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.config import EMBEDDING_DIM, EMBEDDING_MODEL
from app.memory.embedding import embed_texts


def to_pgvector(vec: list[float]) -> str:
    return "[" + ",".join(f"{value:.7g}" for value in vec) + "]"


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


_UPSERT = text("""
    INSERT INTO memory_chunks
        (user_id, source_type, source_id, chunk_index, content, content_hash,
         embedding, embedding_model, embedding_dim, source_created_at)
    VALUES
        (:user_id, :source_type, :source_id, :chunk_index, :content, :content_hash,
         CAST(CAST(:embedding AS text) AS vector), :model, :dim, :source_created_at)
    ON CONFLICT (source_type, source_id, chunk_index) DO UPDATE SET
        content = EXCLUDED.content,
        content_hash = EXCLUDED.content_hash,
        embedding = EXCLUDED.embedding,
        embedding_model = EXCLUDED.embedding_model,
        embedding_dim = EXCLUDED.embedding_dim,
        source_created_at = EXCLUDED.source_created_at,
        created_at = now()
    WHERE memory_chunks.user_id = EXCLUDED.user_id
""")


async def upsert_chunk(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    source_type: str,
    source_id: uuid.UUID,
    chunk_index: int,
    content: str,
    vector: list[float],
    source_created_at: datetime,
) -> None:
    """Upsert one precomputed vector without committing the caller's transaction."""
    result = await db.execute(
        _UPSERT,
        {
            "user_id": user_id,
            "source_type": source_type,
            "source_id": source_id,
            "chunk_index": chunk_index,
            "content": content,
            "content_hash": content_hash(content),
            "embedding": to_pgvector(vector),
            "model": EMBEDDING_MODEL,
            "dim": EMBEDDING_DIM,
            "source_created_at": source_created_at,
        },
    )
    if result.rowcount == 0:
        raise ValueError("This source chunk is already owned by a different user")


async def store_chunk(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    source_type: str,
    source_id: uuid.UUID,
    chunk_index: int,
    content: str,
    source_created_at: datetime,
) -> None:
    """Embed and upsert one chunk; the caller owns the database transaction."""
    [vector] = await embed_texts([content], task_type="RETRIEVAL_DOCUMENT")
    await upsert_chunk(
        db,
        user_id=user_id,
        source_type=source_type,
        source_id=source_id,
        chunk_index=chunk_index,
        content=content,
        vector=vector,
        source_created_at=source_created_at,
    )


async def delete_source_chunks(
    db: AsyncSession,
    *,
    source_type: str,
    source_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    """Delete all chunks for a source inside the caller's transaction."""
    await db.execute(
        text(
            "DELETE FROM memory_chunks WHERE user_id = :user_id "
            "AND source_type = :source_type AND source_id = :source_id"
        ),
        {
            "user_id": user_id,
            "source_type": source_type,
            "source_id": source_id,
        },
    )


async def search_by_vector(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    vector: list[float],
    k: int = 5,
    source_types: Iterable[str] | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> list[dict]:
    if not 1 <= k <= 100:
        raise ValueError("k must be between 1 and 100")
    clauses = ["user_id = :user_id", "embedding_model = :model"]
    params: dict = {"user_id": user_id, "model": EMBEDDING_MODEL,
                    "q": to_pgvector(vector), "k": k}
    if source_types:
        clauses.append("source_type = ANY(:source_types)")
        params["source_types"] = list(source_types)
    if since:
        clauses.append("source_created_at >= :since")
        params["since"] = since
    if until:
        clauses.append("source_created_at < :until")
        params["until"] = until
    sql = text(f"""
        SELECT id, source_type, source_id, chunk_index, content, source_created_at,
               1 - (embedding <=> CAST(CAST(:q AS text) AS vector)) AS similarity
        FROM memory_chunks
        WHERE {" AND ".join(clauses)}
        ORDER BY embedding <=> CAST(CAST(:q AS text) AS vector)
        LIMIT :k
    """)
    rows = (await db.execute(sql, params)).mappings().all()
    return [dict(r) for r in rows]


async def search_chunks(db: AsyncSession, *, user_id: uuid.UUID, query: str,
                        k: int = 5, source_types: Iterable[str] | None = None,
                        since: datetime | None = None,
                        until: datetime | None = None) -> list[dict]:
    [qvec] = await embed_texts([query], task_type="RETRIEVAL_QUERY")
    return await search_by_vector(db, user_id=user_id, vector=qvec, k=k,
                                  source_types=source_types, since=since, until=until)
