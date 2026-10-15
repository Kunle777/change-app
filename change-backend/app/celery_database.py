from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.database import DATABASE_URL


@asynccontextmanager
async def celery_db_session() -> AsyncIterator[AsyncSession]:
    """
    Async session for Celery tasks.

    Creates a fresh engine and connection per invocation using NullPool so that
    asyncpg connections are never reused across the separate event loops that
    asyncio.run() creates and closes for each task execution.

    The existing FastAPI engine (app/database.py) is not affected.
    """
    engine = create_async_engine(
        DATABASE_URL,
        poolclass=NullPool,
        connect_args={"statement_cache_size": 0},
    )
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with factory() as session:
            yield session
    finally:
        await engine.dispose()
