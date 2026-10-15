"""
Regression test: celery_db_session must not raise
"RuntimeError: Event loop is closed" when called from separate asyncio.run()
invocations in the same process, which is exactly the condition that the
--pool=solo Celery worker creates.

Run with:
    set PYTHONPATH=. && venv\\Scripts\\python.exe -m pytest scripts/test_celery_db_loop.py -v
"""
import asyncio
import pytest
from sqlalchemy import text


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _query_once() -> str:
    """Open a session, run a trivial query, commit, and return."""
    from app.celery_database import celery_db_session

    async with celery_db_session() as db:
        result = await db.execute(text("SELECT 1 AS val"))
        row = result.fetchone()
        assert row is not None and row.val == 1
        # Explicit commit mirrors what every real task wrapper does.
        await db.commit()
    return "ok"


def _run_once() -> str:
    """Simulate one Celery task execution: asyncio.run creates+closes a loop."""
    return asyncio.run(_query_once())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_single_invocation():
    """Baseline: one asyncio.run() succeeds."""
    assert _run_once() == "ok"


def test_repeated_invocations_no_event_loop_error():
    """
    Core regression: five sequential asyncio.run() calls in the same process.

    Before the NullPool fix, the second call would raise
    RuntimeError: Event loop is closed because asyncpg reused a connection
    whose transport was bound to the first (now-closed) loop.
    """
    for i in range(5):
        try:
            result = _run_once()
        except RuntimeError as exc:
            pytest.fail(
                f"Invocation {i + 1} raised RuntimeError (likely cross-loop "
                f"connection reuse): {exc}"
            )
        assert result == "ok", f"Invocation {i + 1} returned unexpected value"


def test_session_cleanup_on_exception():
    """
    Engine.dispose() must be called even when the session body raises,
    so no connection is leaked to the next invocation.
    """
    async def _raise():
        from app.celery_database import celery_db_session

        async with celery_db_session() as db:
            await db.execute(text("SELECT 1"))
            raise ValueError("simulated task failure")

    with pytest.raises(ValueError, match="simulated task failure"):
        asyncio.run(_raise())

    # The next invocation must still succeed — engine was disposed cleanly.
    assert _run_once() == "ok"


def test_fastapi_engine_unchanged():
    """
    Importing celery_database must not mutate the FastAPI engine or session
    factory in app.database.
    """
    from app.database import engine as fa_engine, AsyncSessionLocal
    from app.celery_database import celery_db_session

    # The FastAPI engine must still be the same pooled object.
    assert fa_engine.pool.__class__.__name__ != "NullPool", (
        "FastAPI engine was unexpectedly replaced with NullPool"
    )
    # celery_db_session must be a different callable, not AsyncSessionLocal.
    assert celery_db_session is not AsyncSessionLocal
