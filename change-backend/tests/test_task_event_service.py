import os
import unittest
import uuid
from contextlib import AbstractAsyncContextManager
from types import SimpleNamespace
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
from sqlalchemy.exc import IntegrityError

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://test:test@127.0.0.1:5432/change_app_test",
)

from app.tasks.models import TaskEvent, TaskEventOutbox, TaskEventType  # noqa: E402
from app.tasks.task_event_service import deliver_task_event_outbox, log_task_event  # noqa: E402
from app.tasks.service import record_overdue_task_events  # noqa: E402


class FakeSavepoint(AbstractAsyncContextManager):
    def __init__(self, session):
        self.session = session
        self.start = 0

    async def __aenter__(self):
        self.start = len(self.session.pending_events)
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            del self.session.pending_events[self.start :]
        return False


class FakeSession:
    def __init__(self, flush_error=None, execute_side_effect=None):
        self.flush_error = flush_error
        self.pending_events = []
        self.committed_events = []
        self.task_completed = False
        self.execute = AsyncMock(
            side_effect=execute_side_effect,
            return_value=Mock(scalar_one=Mock(return_value="0")),
        )
        self.deleted = []

    def begin_nested(self):
        return FakeSavepoint(self)

    def add(self, event):
        self.pending_events.append(event)

    async def delete(self, item):
        self.deleted.append(item)

    async def flush(self):
        if self.flush_error:
            raise self.flush_error

    async def commit(self):
        self.committed_events.extend(self.pending_events)
        self.pending_events.clear()


class TaskEventServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_event_is_pending_for_callers_commit(self):
        session = FakeSession()
        user_id = uuid.uuid4()
        task_id = uuid.uuid4()

        await log_task_event(
            session,
            user_id=user_id,
            task_id=task_id,
            event_type=TaskEventType.RESCHEDULED,
            metadata={"old_due": None, "new_due": "2026-10-01T09:00:00+00:00"},
        )

        self.assertEqual(len(session.pending_events), 1)
        event = session.pending_events[0]
        self.assertIsInstance(event, TaskEventOutbox)
        self.assertEqual(event.user_id, user_id)
        self.assertEqual(event.task_id, task_id)
        self.assertEqual(event.event_type, "rescheduled")
        self.assertEqual(event.event_metadata["old_due"], None)
        self.assertIsNotNone(event.occurred_at)
        await session.commit()
        self.assertEqual(session.committed_events, [event])

    async def test_event_insert_failure_does_not_block_task_commit(self):
        session = FakeSession(flush_error=RuntimeError("simulated task_events insert failure"))
        session.task_completed = True

        await log_task_event(
            session,
            user_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            event_type=TaskEventType.COMPLETED,
        )
        await session.commit()

        self.assertTrue(session.task_completed)
        self.assertEqual(session.committed_events, [])

    async def test_duplicate_event_conflict_is_swallowed_for_retry_safety(self):
        session = FakeSession(
            flush_error=IntegrityError(
                "insert",
                {},
                SimpleNamespace(constraint_name="uq_task_events_overdue_deadline"),
            ),
        )

        await log_task_event(
            session,
            user_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            event_type=TaskEventType.OVERDUE,
            metadata={"due_date": "2026-09-01T00:00:00+00:00"},
        )

        self.assertEqual(session.pending_events, [])

    def test_database_has_unique_indexes_for_retryable_events(self):
        event_index_names = {index.name for index in TaskEvent.__table__.indexes}
        outbox_index_names = {index.name for index in TaskEventOutbox.__table__.indexes}
        self.assertIn("uq_task_events_overdue_deadline", event_index_names)
        self.assertIn("uq_task_events_reminder_open_notification", event_index_names)
        self.assertIn("uq_task_event_outbox_overdue_deadline", outbox_index_names)
        self.assertIn("uq_task_event_outbox_reminder_open_notification", outbox_index_names)

    async def test_outbox_delivery_moves_event_and_removes_queue_item(self):
        queued = TaskEventOutbox(
            id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            event_type="created",
            occurred_at=datetime.now(timezone.utc),
            event_metadata={"source": "test"},
        )
        queued_result = Mock()
        queued_result.scalars.return_value.all.return_value = [queued]
        timeout_result = Mock(scalar_one=Mock(return_value="0"))
        db = FakeSession(execute_side_effect=[queued_result, timeout_result, Mock(), Mock()])

        delivered = await deliver_task_event_outbox(db)

        self.assertEqual(delivered, 1)
        self.assertEqual(db.deleted, [queued])
        self.assertIsInstance(db.committed_events[0], TaskEvent)
        self.assertEqual(db.committed_events[0].id, queued.id)

    async def test_failed_outbox_delivery_keeps_entry_for_retry(self):
        queued = TaskEventOutbox(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            event_type="created",
            occurred_at=datetime.now(timezone.utc),
            event_metadata={},
        )
        queued_result = Mock()
        queued_result.scalars.return_value.all.return_value = [queued]
        timeout_result = Mock(scalar_one=Mock(return_value="0"))
        db = FakeSession(
            flush_error=RuntimeError("simulated task_events insert failure"),
            execute_side_effect=[queued_result, timeout_result, Mock()],
        )

        delivered = await deliver_task_event_outbox(db)

        self.assertEqual(delivered, 0)
        self.assertEqual(db.deleted, [])
        self.assertEqual(queued.attempts, 1)
        self.assertEqual(queued.last_error, "RuntimeError")

    async def test_overdue_processor_skips_a_deadline_already_recorded(self):
        task_id = uuid.uuid4()
        due_date = datetime(2026, 9, 1, tzinfo=timezone.utc)
        task = SimpleNamespace(id=task_id, user_id=uuid.uuid4(), due_date=due_date)
        task_result = Mock()
        task_result.scalars.return_value.all.return_value = [task]
        event_result = Mock()
        event_result.all.return_value = [(task_id, due_date.isoformat())]
        db = SimpleNamespace(
            execute=AsyncMock(side_effect=[task_result, event_result]),
            commit=AsyncMock(),
        )

        with patch("app.tasks.service.log_task_event", new_callable=AsyncMock) as log_event:
            recorded = await record_overdue_task_events(db)

        self.assertEqual(recorded, 0)
        log_event.assert_not_awaited()
        db.commit.assert_awaited_once()

    async def test_overdue_processor_records_a_new_deadline(self):
        task_id = uuid.uuid4()
        user_id = uuid.uuid4()
        due_date = datetime(2026, 9, 1, tzinfo=timezone.utc)
        task = SimpleNamespace(id=task_id, user_id=user_id, due_date=due_date)
        task_result = Mock()
        task_result.scalars.return_value.all.return_value = [task]
        event_result = Mock()
        event_result.all.return_value = []
        db = SimpleNamespace(
            execute=AsyncMock(side_effect=[task_result, event_result]),
            commit=AsyncMock(),
        )

        with patch("app.tasks.service.log_task_event", new_callable=AsyncMock) as log_event:
            recorded = await record_overdue_task_events(db)

        self.assertEqual(recorded, 1)
        log_event.assert_awaited_once_with(
            db,
            user_id=user_id,
            task_id=task_id,
            event_type=TaskEventType.OVERDUE,
            metadata={"due_date": due_date.isoformat()},
        )


if __name__ == "__main__":
    unittest.main()
