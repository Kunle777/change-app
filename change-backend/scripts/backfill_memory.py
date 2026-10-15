"""
One-shot backfill: index all existing brain dumps and check-ins into memory_chunks.
Run from change-backend/:
    PYTHONPATH=$PWD python scripts/backfill_memory.py
"""
import asyncio
import logging

from app.database import AsyncSessionLocal
from app.memory.indexer import sweep_memory_index

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

BATCH = 500


async def main() -> None:
    total = {"indexed": 0, "failed": 0, "orphans_deleted": 0, "reembedded": 0}
    async with AsyncSessionLocal() as db:
        log.info("Starting memory backfill (batch size %d) …", BATCH)
        stats = await sweep_memory_index(db, limit=BATCH)
        for key in total:
            total[key] += stats.get(key, 0)

    log.info(
        "Done — indexed: %d  failed: %d  orphans deleted: %d  re-embedded: %d",
        total["indexed"],
        total["failed"],
        total["orphans_deleted"],
        total["reembedded"],
    )
    if total["failed"]:
        raise SystemExit(1)


asyncio.run(main())
