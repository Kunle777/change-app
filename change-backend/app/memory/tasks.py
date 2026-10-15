import asyncio
import logging
import uuid

from celery_app import celery_app

from app.celery_database import celery_db_session
from app.memory.indexer import index_source, sweep_memory_index


logger = logging.getLogger(__name__)


async def _index_source_async(source_type: str, source_id: str, user_id: str) -> int:
    async with celery_db_session() as db:
        return await index_source(
            db,
            source_type=source_type,
            source_id=uuid.UUID(source_id),
            user_id=uuid.UUID(user_id),
        )


@celery_app.task(name="app.memory.tasks.index_memory_source_job")
def index_memory_source_job(source_type: str, source_id: str, user_id: str) -> int:
    return asyncio.run(_index_source_async(source_type, source_id, user_id))


async def _sweep_memory_index_async() -> dict[str, int]:
    async with celery_db_session() as db:
        return await sweep_memory_index(db)


@celery_app.task(name="app.memory.tasks.sweep_memory_index_job")
def sweep_memory_index_job() -> dict[str, int]:
    return asyncio.run(_sweep_memory_index_async())


def enqueue_memory_source_index(
    *,
    source_type: str,
    source_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    try:
        index_memory_source_job.delay(source_type, str(source_id), str(user_id))
    except Exception:
        logger.exception(
            "Could not enqueue memory indexing for source type %s; periodic sweep will recover it",
            source_type,
        )
        return False
    return True
