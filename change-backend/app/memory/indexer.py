import logging
import uuid

from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.braindump.models import BrainDump
from app.checkins.models import CheckIn
from app.memory.config import EMBEDDING_DIM, EMBEDDING_MODEL
from app.memory.embedding import embed_texts
from app.memory.models import MemoryChunk
from app.memory.service import (
    content_hash,
    delete_source_chunks,
    to_pgvector,
    upsert_chunk,
)
from app.memory.sources import load_source


logger = logging.getLogger(__name__)


async def ai_allowed(db: AsyncSession, user_id: uuid.UUID) -> bool:
    row = (
        await db.execute(
            text(
                "SELECT ai_enabled FROM feature_entitlements "
                "WHERE user_id = :user_id"
            ),
            {"user_id": user_id},
        )
    ).first()
    return bool(row[0]) if row is not None else False


async def index_source(
    db: AsyncSession,
    *,
    source_type: str,
    source_id: uuid.UUID,
    user_id: uuid.UUID,
) -> int:
    if not await ai_allowed(db, user_id):
        logger.info(
            "Memory indexing skipped because AI is disabled or no entitlement exists"
        )
        return 0

    loaded = await load_source(
        db,
        source_type=source_type,
        source_id=source_id,
        user_id=user_id,
    )
    if loaded is None:
        return 0
    contents, source_created_at = loaded
    if not contents:
        await delete_source_chunks(
            db,
            source_type=source_type,
            source_id=source_id,
            user_id=user_id,
        )
        await db.commit()
        return 0

    existing_rows = (
        await db.execute(
            text(
                "SELECT chunk_index, content_hash, embedding_model FROM memory_chunks "
                "WHERE user_id = :user_id AND source_type = :source_type "
                "AND source_id = :source_id"
            ),
            {
                "user_id": user_id,
                "source_type": source_type,
                "source_id": source_id,
            },
        )
    ).all()
    existing = {
        row.chunk_index: (row.content_hash, row.embedding_model)
        for row in existing_rows
    }
    to_embed = [
        (index, content)
        for index, content in enumerate(contents)
        if existing.get(index) != (content_hash(content), EMBEDDING_MODEL)
    ]

    if to_embed:
        vectors = await embed_texts(
            [content for _, content in to_embed],
            task_type="RETRIEVAL_DOCUMENT",
        )
        if len(vectors) != len(to_embed):
            raise ValueError("Embedding response count did not match pending memory chunks")
        for (chunk_index, content), vector in zip(to_embed, vectors):
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

    params = {
        "user_id": user_id,
        "source_type": source_type,
        "source_id": source_id,
    }
    await db.execute(
        text(
            "DELETE FROM memory_chunks WHERE user_id = :user_id "
            "AND source_type = :source_type AND source_id = :source_id "
            "AND chunk_index >= :chunk_count"
        ),
        {**params, "chunk_count": len(contents)},
    )
    await db.execute(
        text(
            "UPDATE memory_chunks SET created_at = now() "
            "WHERE user_id = :user_id AND source_type = :source_type "
            "AND source_id = :source_id"
        ),
        params,
    )
    await db.commit()
    return len(to_embed)


def _ai_enabled_for(table_name: str):
    if table_name not in {BrainDump.__tablename__, CheckIn.__tablename__}:
        raise ValueError("Unsupported memory source table")
    return text(
        "EXISTS (SELECT 1 FROM feature_entitlements fe "
        f"WHERE fe.user_id = {table_name}.user_id AND fe.ai_enabled IS TRUE)"
    )


async def delete_orphans(db: AsyncSession) -> int:
    result = await db.execute(
        text(
            f"""
            DELETE FROM memory_chunks m
            WHERE (m.source_type = 'brain_dump' AND NOT EXISTS
                     (SELECT 1 FROM {BrainDump.__tablename__} b WHERE b.id = m.source_id))
               OR (m.source_type = 'check_in' AND NOT EXISTS
                     (SELECT 1 FROM {CheckIn.__tablename__} c WHERE c.id = m.source_id))
            """
        )
    )
    await db.commit()
    return result.rowcount or 0


async def reembed_stale_model_chunks(
    db: AsyncSession,
    *,
    limit: int = 50,
) -> int:
    rows = (
        await db.execute(
            text(
                "SELECT mc.id, mc.content FROM memory_chunks mc "
                "JOIN feature_entitlements fe ON fe.user_id = mc.user_id "
                "WHERE mc.embedding_model <> :model AND fe.ai_enabled IS TRUE "
                "ORDER BY mc.created_at LIMIT :limit"
            ),
            {"model": EMBEDDING_MODEL, "limit": limit},
        )
    ).all()
    if not rows:
        return 0

    vectors = await embed_texts(
        [row.content for row in rows],
        task_type="RETRIEVAL_DOCUMENT",
    )
    if len(vectors) != len(rows):
        raise ValueError("Embedding response count did not match stale memory chunks")
    for row, vector in zip(rows, vectors):
        await db.execute(
            text(
                "UPDATE memory_chunks SET "
                "embedding = CAST(CAST(:embedding AS text) AS vector), "
                "embedding_model = :model, embedding_dim = :dimension, created_at = now() "
                "WHERE id = :id"
            ),
            {
                "embedding": to_pgvector(vector),
                "model": EMBEDDING_MODEL,
                "dimension": EMBEDDING_DIM,
                "id": row.id,
            },
        )
    await db.commit()
    return len(rows)


async def sweep_memory_index(
    db: AsyncSession,
    *,
    limit: int = 50,
) -> dict[str, int]:
    if limit < 1:
        raise ValueError("limit must be positive")

    stats = {"orphans_deleted": await delete_orphans(db), "indexed": 0, "failed": 0, "reembedded": 0}

    dump_updated = (
        BrainDump.updated_at
        if hasattr(BrainDump, "updated_at")
        else BrainDump.created_at
    )
    first_dump = and_(
        MemoryChunk.source_type == "brain_dump",
        MemoryChunk.source_id == BrainDump.id,
        MemoryChunk.user_id == BrainDump.user_id,
        MemoryChunk.chunk_index == 0,
    )
    dumps = (
        await db.execute(
            select(BrainDump.id, BrainDump.user_id)
            .select_from(BrainDump)
            .outerjoin(MemoryChunk, first_dump)
            .where(
                func.length(func.trim(BrainDump.content)) > 0,
                _ai_enabled_for(BrainDump.__tablename__),
                or_(
                    MemoryChunk.id.is_(None),
                    dump_updated > MemoryChunk.created_at,
                    MemoryChunk.created_at
                    < text("now() - interval '15 minutes'"),
                ),
            )
            .order_by(BrainDump.created_at.desc())
            .limit(limit)
        )
    ).all()

    first_check_in = and_(
        MemoryChunk.source_type == "check_in",
        MemoryChunk.source_id == CheckIn.id,
        MemoryChunk.user_id == CheckIn.user_id,
        MemoryChunk.chunk_index == 0,
    )
    has_check_in_text = or_(
        func.length(func.trim(func.coalesce(CheckIn.goal_today, ""))) > 0,
        func.length(func.trim(func.coalesce(CheckIn.reflection, ""))) > 0,
    )
    check_ins = (
        await db.execute(
            select(CheckIn.id, CheckIn.user_id)
            .select_from(CheckIn)
            .outerjoin(MemoryChunk, first_check_in)
            .where(
                has_check_in_text,
                _ai_enabled_for(CheckIn.__tablename__),
                or_(
                    MemoryChunk.id.is_(None),
                    MemoryChunk.created_at
                    < text("now() - interval '15 minutes'"),
                ),
            )
            .order_by(CheckIn.created_at.desc())
            .limit(limit)
        )
    ).all()

    work = [
        ("brain_dump", row.id, row.user_id)
        for row in dumps
    ] + [
        ("check_in", row.id, row.user_id)
        for row in check_ins
    ]

    consecutive_failures = 0
    for source_type, source_id, user_id in work:
        try:
            await index_source(
                db,
                source_type=source_type,
                source_id=source_id,
                user_id=user_id,
            )
            stats["indexed"] += 1
            consecutive_failures = 0
        except Exception:
            await db.rollback()
            stats["failed"] += 1
            consecutive_failures += 1
            logger.exception("Memory indexing failed for source type %s", source_type)
            if consecutive_failures >= 3:
                break

    try:
        stats["reembedded"] = await reembed_stale_model_chunks(db, limit=limit)
    except Exception:
        await db.rollback()
        logger.exception("Memory re-embedding sweep failed")

    return stats
