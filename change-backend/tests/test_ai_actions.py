import os
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://test:test@127.0.0.1:5432/change_app_test",
)

from app.ai import action_service  # noqa: E402
from app.ai import routers as ai_routers  # noqa: E402
from app.ai import service as ai_service  # noqa: E402
from app.ai import tool_executor  # noqa: E402


class FakeResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def scalars(self):
        return self

    def all(self):
        return self.value


class FakeSession:
    def __init__(self, result=None):
        self.execute = AsyncMock(return_value=FakeResult(result))
        self.add = Mock()
        self.flush = AsyncMock()
        self.refresh = AsyncMock()
        self.commit = AsyncMock()
        self.rollback = AsyncMock()


class AIActionTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_tool_auto_executes_without_staging_confirmation(self):
        user = SimpleNamespace(id=uuid.uuid4())
        db = FakeSession()
        with patch.object(
            action_service,
            "execute_tool",
            new=AsyncMock(return_value={"status": "created", "task_id": "task-id"}),
        ) as execute:
            result = await action_service.handle_tool_call(
                db, user, uuid.uuid4(), "create_task", {"title": "Call mum"},
                eligible=True,
            )

        self.assertEqual(result["status"], "created")
        execute.assert_awaited_once()
        db.commit.assert_not_awaited()
        db.add.assert_not_called()

    async def test_update_tool_stages_confirmation_instead_of_executing(self):
        user = SimpleNamespace(id=uuid.uuid4())
        db = FakeSession()
        with patch.object(
            action_service,
            "validate_confirmation_tool",
            new=AsyncMock(return_value=({"task_id": str(uuid.uuid4()), "priority": "high"}, "Update task.")),
        ), patch.object(action_service, "execute_tool", new=AsyncMock()) as execute:
            result = await action_service.handle_tool_call(
                db,
                user,
                uuid.uuid4(),
                "update_task",
                {"task_id": str(uuid.uuid4()), "priority": "high"},
                eligible=True,
            )

        self.assertEqual(result["status"], "awaiting_confirmation")
        self.assertIsNotNone(result["pending_action_id"])
        execute.assert_not_awaited()
        db.add.assert_called_once()
        db.flush.assert_awaited_once()
        db.commit.assert_not_awaited()

    async def test_expired_confirmation_never_executes(self):
        pending = SimpleNamespace(
            id=uuid.uuid4(),
            status="pending",
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
        user = SimpleNamespace(id=uuid.uuid4())
        db = FakeSession(pending)
        with patch.object(action_service, "execute_tool", new=AsyncMock()) as execute:
            result = await action_service.confirm_pending_action(db, user, pending.id)

        self.assertEqual(result["status"], "expired")
        self.assertEqual(pending.status, "expired")
        execute.assert_not_awaited()
        db.commit.assert_awaited_once()

    async def test_successful_confirmation_commits_mutation_and_status_once(self):
        pending = SimpleNamespace(
            id=uuid.uuid4(),
            status="pending",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            tool_name="update_task",
            arguments={"task_id": str(uuid.uuid4()), "priority": "high"},
        )
        user = SimpleNamespace(id=uuid.uuid4())
        db = FakeSession(pending)
        with patch.object(
            action_service,
            "execute_tool",
            new=AsyncMock(return_value={"status": "updated", "task_id": pending.arguments["task_id"]}),
        ) as execute:
            result = await action_service.confirm_pending_action(db, user, pending.id)

        self.assertEqual(result["status"], "updated")
        self.assertEqual(pending.status, "confirmed")
        execute.assert_awaited_once()
        db.commit.assert_awaited_once()
        db.rollback.assert_not_awaited()

    async def test_retryable_confirmation_error_rolls_back_and_keeps_action_pending(self):
        pending = SimpleNamespace(
            id=uuid.uuid4(),
            status="pending",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            tool_name="update_task",
            arguments={"task_id": str(uuid.uuid4()), "priority": "high"},
            outcome=None,
        )
        db = FakeSession(pending)
        with patch.object(
            action_service,
            "execute_tool",
            new=AsyncMock(return_value={"status": "error", "reason": "verification failed"}),
        ):
            result = await action_service.confirm_pending_action(
                db, SimpleNamespace(id=uuid.uuid4()), pending.id
            )

        self.assertEqual(result, {"status": "error", "retryable": True})
        self.assertEqual(pending.status, "pending")
        db.rollback.assert_awaited_once()
        db.commit.assert_not_awaited()

    async def test_confirmation_route_returns_safe_retryable_error_on_exception(self):
        error = RuntimeError("database detail and internal task identifier")
        request = SimpleNamespace(state=SimpleNamespace(request_id="request-ref"))
        with patch.object(
            ai_routers.action_service,
            "resolve_action_reference",
            new=AsyncMock(return_value=uuid.uuid4()),
        ), patch.object(
            ai_routers.action_service,
            "confirm_pending_action",
            new=AsyncMock(side_effect=error),
        ):
            result = await ai_routers.confirm_pending_action_route(
                "pa_" + ("a" * 64),
                request,
                FakeSession(),
                SimpleNamespace(id=uuid.uuid4()),
            )

        self.assertEqual(result, {"status": "error", "retryable": True})
        self.assertNotIn("internal task identifier", str(result))

    async def test_confirmed_action_cannot_execute_twice(self):
        pending = SimpleNamespace(
            id=uuid.uuid4(),
            status="pending",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            tool_name="update_task",
            arguments={"task_id": str(uuid.uuid4()), "priority": "high"},
        )
        user = SimpleNamespace(id=uuid.uuid4())
        db = FakeSession(pending)
        db.execute.side_effect = [FakeResult(pending), FakeResult(None)]
        with patch.object(
            action_service,
            "execute_tool",
            new=AsyncMock(return_value={"status": "updated", "task_id": pending.arguments["task_id"]}),
        ) as execute:
            first = await action_service.confirm_pending_action(db, user, pending.id)
            second = await action_service.confirm_pending_action(db, user, pending.id)

        self.assertEqual(first["status"], "updated")
        self.assertEqual(second["status"], "error")
        execute.assert_awaited_once()
        db.commit.assert_awaited_once()

    async def test_stale_proposal_does_not_mutate_task(self):
        task = SimpleNamespace(
            id=uuid.uuid4(),
            title="Write report",
            due_date=None,
            priority=tool_executor.PriorityEnum.medium,
            status=tool_executor.StatusEnum.pending,
            is_deleted=False,
            created_at=None,
        )
        user = SimpleNamespace(id=uuid.uuid4())
        db = FakeSession()
        with patch.object(
            tool_executor.task_service,
            "get_task_by_id",
            new=AsyncMock(return_value=task),
        ), patch.object(
            tool_executor.task_service,
            "update_task",
            new=AsyncMock(),
        ) as update:
            result = await tool_executor.execute_tool(
                db,
                user,
                "update_task",
                {
                    "task_id": str(task.id),
                    "priority": "high",
                    "_expected_state": {"due_date": None, "priority": "low"},
                },
            )

        self.assertEqual(result["status"], "stale")
        update.assert_not_awaited()

    async def test_confirmation_rolls_back_task_mutation_if_status_flip_fails(self):
        pending = SimpleNamespace(
            id=uuid.uuid4(),
            status="pending",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            tool_name="update_task",
            arguments={"task_id": str(uuid.uuid4()), "priority": "high"},
        )
        user = SimpleNamespace(id=uuid.uuid4())
        task_state = {"changed": False}

        async def fail_after_mutation(*args, **kwargs):
            task_state["changed"] = True
            raise RuntimeError("simulated failure before confirmation commit")

        async def rollback_transaction():
            task_state["changed"] = False

        db = FakeSession(pending)
        db.rollback.side_effect = rollback_transaction
        with patch.object(action_service, "execute_tool", side_effect=fail_after_mutation):
            with self.assertRaisesRegex(RuntimeError, "simulated failure"):
                await action_service.confirm_pending_action(db, user, pending.id)

        self.assertFalse(task_state["changed"])
        self.assertEqual(pending.status, "pending")
        db.rollback.assert_awaited_once()
        db.commit.assert_not_awaited()

    async def test_confirmation_rolls_back_when_database_commit_fails(self):
        pending = SimpleNamespace(
            id=uuid.uuid4(),
            status="pending",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            tool_name="update_task",
            arguments={"task_id": str(uuid.uuid4()), "priority": "high"},
        )
        user = SimpleNamespace(id=uuid.uuid4())
        mutation = {"applied": False}
        db = FakeSession(pending)
        db.commit.side_effect = RuntimeError("simulated database commit failure")

        async def rollback_transaction():
            mutation["applied"] = False
            pending.status = "pending"

        async def execute_mutation(*args, **kwargs):
            mutation["applied"] = True
            return {"status": "updated"}

        db.rollback.side_effect = rollback_transaction
        with patch.object(action_service, "execute_tool", side_effect=execute_mutation):
            with self.assertRaisesRegex(RuntimeError, "commit failure"):
                await action_service.confirm_pending_action(db, user, pending.id)

        self.assertFalse(mutation["applied"])
        self.assertEqual(pending.status, "pending")
        db.rollback.assert_awaited_once()

    async def test_pending_action_is_scoped_to_authenticated_user(self):
        user = SimpleNamespace(id=uuid.uuid4())
        pending_id = uuid.uuid4()
        db = FakeSession(None)
        with patch.object(action_service, "execute_tool", new=AsyncMock()) as execute:
            result = await action_service.confirm_pending_action(db, user, pending_id)
        self.assertEqual(result["status"], "error")
        execute.assert_not_awaited()
        query = str(db.execute.await_args.args[0].whereclause)
        self.assertIn("pending_actions.user_id", query)

    async def test_update_tool_rejects_task_not_owned_by_user(self):
        user = SimpleNamespace(id=uuid.uuid4())
        db = FakeSession()
        task_id = uuid.uuid4()
        with patch.object(tool_executor.task_service, "get_task_by_id", new=AsyncMock(return_value=None)):
            result = await tool_executor.execute_tool(
                db,
                user,
                "update_task",
                {"task_id": str(task_id), "priority": "high"},
            )

        self.assertEqual(result["status"], "not_found")

    async def test_task_name_resolution_is_owner_scoped_and_fuzzy(self):
        user = SimpleNamespace(id=uuid.uuid4(), last_active_timezone="Africa/Lagos")
        task = SimpleNamespace(
            id=uuid.uuid4(),
            title="Finish website",
            due_date=None,
            priority=tool_executor.PriorityEnum.medium,
            status=tool_executor.StatusEnum.pending,
            is_deleted=False,
            created_at=None,
        )
        db = FakeSession([task])
        result = await tool_executor.validate_confirmation_tool(
            db, user, "update_task",
            {"task_name": "Finsh websitte", "priority": "high"},
        )
        self.assertIsInstance(result, tuple)
        self.assertEqual(result[0]["task_id"], str(task.id))
        where = str(db.execute.await_args.args[0].whereclause)
        self.assertIn("tasks.user_id", where)
        self.assertIn(user.id, db.execute.await_args.args[0].compile().params.values())

    async def test_multiple_matching_task_names_require_selection_without_ids(self):
        user = SimpleNamespace(id=uuid.uuid4(), last_active_timezone="Africa/Lagos")
        tasks = [
            SimpleNamespace(
                id=uuid.uuid4(),
                title=title,
                due_date=None,
                priority=tool_executor.PriorityEnum.medium,
                status=tool_executor.StatusEnum.pending,
                is_deleted=False,
                created_at=None,
            )
            for title in ("Sing Barry", "Sing Bahaub")
        ]
        result = await tool_executor.validate_confirmation_tool(
            FakeSession(tasks), user, "update_task",
            {"task_name": "Sing", "priority": "high"},
        )
        self.assertEqual(result["status"], "ambiguous")
        self.assertEqual(len(result["candidates"]), 2)
        self.assertNotIn("id", result["candidates"][0])

    async def test_invalid_task_id_and_missing_update_fields_are_rejected(self):
        user = SimpleNamespace(id=uuid.uuid4(), last_active_timezone="Africa/Lagos")
        with self.assertRaisesRegex(ValueError, "valid UUID"):
            await tool_executor.validate_confirmation_tool(
                FakeSession(), user, "update_task", {"task_id": "not-a-uuid", "due_date": "2026-10-19"}
            )
        with self.assertRaisesRegex(ValueError, "requires a due_date or priority"):
            await tool_executor.validate_confirmation_tool(
                FakeSession(), user, "update_task", {"task_id": str(uuid.uuid4())}
            )

    async def test_time_is_preserved_in_user_timezone_and_date_only_is_rejected(self):
        user = SimpleNamespace(id=uuid.uuid4(), last_active_timezone="Africa/Lagos")
        due = tool_executor._parse_due_date("2026-10-19T18:00:00", user)
        self.assertEqual(due, datetime(2026, 10, 19, 17, 0, tzinfo=timezone.utc))
        tool_executor._validate_requested_clock(
            "2026-10-19T18:00:00", user, "Today by 6 pm"
        )
        with self.assertRaisesRegex(ValueError, "does not preserve"):
            tool_executor._validate_requested_clock(
                "2026-10-19", user, "Today by 6 pm"
            )
        with self.assertRaisesRegex(ValueError, "No specific time was requested"):
            tool_executor._validate_requested_clock(
                "2026-10-19T18:00:00", user, "Move it to tomorrow"
            )

    async def test_reschedule_confirmation_executes_the_exact_requested_local_time(self):
        task = SimpleNamespace(
            id=uuid.uuid4(),
            title="Sing barry",
            due_date=None,
            priority=tool_executor.PriorityEnum.medium,
            status=tool_executor.StatusEnum.pending,
            is_deleted=False,
        )
        user = SimpleNamespace(id=uuid.uuid4(), last_active_timezone="Africa/Lagos")
        db = FakeSession()

        async def persist_update(*args, task_data, **kwargs):
            task.due_date = task_data.due_date
            task.due_date_is_all_day = task_data.due_date_is_all_day
            return task

        with patch.object(
            tool_executor.task_service, "get_task_by_id", new=AsyncMock(return_value=task)
        ), patch.object(
            tool_executor.task_service, "update_task", new=AsyncMock(side_effect=persist_update)
        ) as update:
            proposal = await tool_executor.validate_confirmation_tool(
                db,
                user,
                "update_task",
                {"task_id": str(task.id), "due_date": "2026-10-19T18:00:00"},
                request_message="Today by 6 pm",
            )
            arguments, summary = proposal
            result = await tool_executor.execute_tool(
                db, user, "update_task", arguments
            )
        self.assertIn("Sing barry", summary)
        self.assertEqual(result["status"], "updated")
        self.assertEqual(
            task.due_date,
            datetime(2026, 10, 19, 17, 0, tzinfo=timezone.utc),
        )
        submitted = update.await_args.kwargs["task_data"]
        self.assertEqual(
            submitted.due_date,
            datetime(2026, 10, 19, 17, 0, tzinfo=timezone.utc),
        )

    async def test_date_only_deadline_flag_survives_pending_confirmation(self):
        task = SimpleNamespace(
            id=uuid.uuid4(),
            title="Sing barry",
            due_date=None,
            due_date_is_all_day=False,
            priority=tool_executor.PriorityEnum.medium,
            status=tool_executor.StatusEnum.pending,
            is_deleted=False,
        )
        user = SimpleNamespace(id=uuid.uuid4(), last_active_timezone="Africa/Lagos")
        db = FakeSession()

        async def persist_update(*args, task_data, **kwargs):
            task.due_date = task_data.due_date
            task.due_date_is_all_day = task_data.due_date_is_all_day
            return task

        with patch.object(
            tool_executor.task_service, "get_task_by_id", new=AsyncMock(return_value=task)
        ), patch.object(
            tool_executor.task_service, "update_task", new=AsyncMock(side_effect=persist_update)
        ) as update:
            proposal = await tool_executor.validate_confirmation_tool(
                db,
                user,
                "update_task",
                {"task_id": str(task.id), "due_date": "2026-10-19"},
                request_message="Reschedule Sing barry to 2026-10-19",
            )
            arguments, _ = proposal
            result = await tool_executor.execute_tool(db, user, "update_task", arguments)

        self.assertEqual(result["status"], "updated")
        self.assertTrue(update.await_args.kwargs["task_data"].due_date_is_all_day)
        self.assertTrue(task.due_date_is_all_day)

    async def test_update_is_not_reported_successful_when_readback_differs(self):
        task = SimpleNamespace(
            id=uuid.uuid4(),
            title="Finish website",
            due_date=None,
            due_date_is_all_day=False,
            priority=tool_executor.PriorityEnum.medium,
            status=tool_executor.StatusEnum.pending,
            is_deleted=False,
        )
        user = SimpleNamespace(id=uuid.uuid4(), last_active_timezone="Africa/Lagos")
        db = FakeSession()
        with patch.object(
            tool_executor.task_service, "get_task_by_id", new=AsyncMock(return_value=task)
        ), patch.object(
            tool_executor.task_service, "update_task", new=AsyncMock(return_value=task)
        ):
            proposal = await tool_executor.validate_confirmation_tool(
                db,
                user,
                "update_task",
                {"task_id": str(task.id), "due_date": "2026-10-19T18:00:00"},
            )
            result = await tool_executor.execute_tool(db, user, "update_task", proposal[0])

        self.assertEqual(result["status"], "error")

    async def test_ineligible_or_malformed_model_tool_call_never_executes(self):
        user = SimpleNamespace(id=uuid.uuid4())
        db = FakeSession()
        with patch.object(action_service, "execute_tool", new=AsyncMock()) as execute:
            denied = await action_service.handle_tool_call(
                db, user, uuid.uuid4(), "create_task", {"title": "Call mum"}, eligible=False
            )
            malformed = await action_service.handle_tool_call(
                db, user, uuid.uuid4(), "create_task", ["not", "an", "object"],
                eligible=True, force_confirmation=True,
            )
        self.assertEqual(denied["status"], "error")
        self.assertEqual(malformed["status"], "error")
        execute.assert_not_awaited()
        db.add.assert_not_called()

    async def test_completed_task_is_not_eligible_for_ai_update(self):
        task = SimpleNamespace(
            id=uuid.uuid4(),
            title="Completed task",
            due_date=None,
            priority=tool_executor.PriorityEnum.medium,
            status=tool_executor.StatusEnum.completed,
            is_deleted=False,
        )
        user = SimpleNamespace(id=uuid.uuid4(), last_active_timezone="Africa/Lagos")
        with patch.object(
            tool_executor.task_service, "get_task_by_id", new=AsyncMock(return_value=task)
        ):
            result = await tool_executor.validate_confirmation_tool(
                FakeSession(), user, "update_task",
                {"task_id": str(task.id), "priority": "high"},
            )
        self.assertEqual(result["status"], "not_found")

    async def test_rejection_persists_terminal_outcome(self):
        pending = SimpleNamespace(
            id=uuid.uuid4(),
            status="pending",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            outcome=None,
        )
        db = FakeSession(pending)
        result = await action_service.reject_pending_action(
            db, SimpleNamespace(id=uuid.uuid4()), pending.id
        )
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(pending.outcome, {"status": "rejected"})
        db.commit.assert_awaited_once()

    async def test_repeated_confirmation_returns_stored_outcome_without_reexecution(self):
        pending = SimpleNamespace(
            id=uuid.uuid4(),
            status="confirmed",
            outcome={"status": "updated"},
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            tool_name="update_task",
            arguments={"task_id": str(uuid.uuid4()), "priority": "high"},
        )
        db = FakeSession(pending)
        with patch.object(action_service, "execute_tool", new=AsyncMock()) as execute:
            result = await action_service.confirm_pending_action(
                db, SimpleNamespace(id=uuid.uuid4()), pending.id
            )
        self.assertEqual(result["status"], "updated")
        self.assertTrue(result["already_resolved"])
        execute.assert_not_awaited()

    async def test_chat_yes_confirms_the_latest_pending_action(self):
        pending_id = uuid.uuid4()
        conversation = SimpleNamespace(id=uuid.uuid4(), updated_at=datetime.now(timezone.utc))
        latest = SimpleNamespace(pending_action_id=pending_id)
        db = FakeSession(SimpleNamespace(id=pending_id, status="pending"))
        user = SimpleNamespace(id=uuid.uuid4())
        with patch.object(
            ai_service, "continue_conversation", new=AsyncMock(return_value=conversation)
        ), patch.object(
            ai_service, "_latest_interaction", new=AsyncMock(return_value=latest)
        ), patch.object(
            action_service, "confirm_pending_action",
            new=AsyncMock(return_value={"status": "updated"}),
        ) as confirm, patch.object(
            ai_service, "assemble_coaching_context",
            new=AsyncMock(side_effect=AssertionError("confirmation must not call Gemini")),
        ):
            result = await ai_service.handle_chat(
                db, user, "Yes", conversation_id=conversation.id
            )
        self.assertEqual(
            result.resolved_action_id,
            action_service.opaque_action_reference(user.id, pending_id),
        )
        self.assertEqual(result.resolved_action_status, "updated")
        confirm.assert_awaited_once_with(db, user, pending_id, commit=False)

    async def test_chat_retry_can_confirm_a_still_pending_action(self):
        pending_id = uuid.uuid4()
        conversation = SimpleNamespace(id=uuid.uuid4(), updated_at=datetime.now(timezone.utc))
        latest = SimpleNamespace(
            pending_action_id=None,
            resolved_action_id=pending_id,
            resolved_action_status="pending",
        )
        db = FakeSession(SimpleNamespace(id=pending_id, status="pending"))
        user = SimpleNamespace(id=uuid.uuid4())
        with patch.object(
            ai_service, "continue_conversation", new=AsyncMock(return_value=conversation)
        ), patch.object(
            ai_service, "_latest_interaction", new=AsyncMock(return_value=latest)
        ), patch.object(
            action_service, "confirm_pending_action",
            new=AsyncMock(return_value={"status": "updated"}),
        ) as confirm, patch.object(
            ai_service, "assemble_coaching_context",
            new=AsyncMock(side_effect=AssertionError("confirmation must not call Gemini")),
        ):
            result = await ai_service.handle_chat(
                db, user, "Yes", conversation_id=conversation.id
            )
        self.assertEqual(
            result.resolved_action_id,
            action_service.opaque_action_reference(user.id, pending_id),
        )
        self.assertEqual(result.resolved_action_status, "updated")
        confirm.assert_awaited_once_with(db, user, pending_id, commit=False)

    async def test_retryable_chat_confirmation_keeps_action_pending(self):
        pending_id = uuid.uuid4()
        conversation = SimpleNamespace(id=uuid.uuid4(), updated_at=datetime.now(timezone.utc))
        latest = SimpleNamespace(pending_action_id=pending_id)
        db = FakeSession(SimpleNamespace(id=pending_id, status="pending"))
        user = SimpleNamespace(id=uuid.uuid4())
        with patch.object(
            ai_service, "continue_conversation", new=AsyncMock(return_value=conversation)
        ), patch.object(
            ai_service, "_latest_interaction", new=AsyncMock(return_value=latest)
        ), patch.object(
            action_service, "confirm_pending_action",
            new=AsyncMock(return_value={"status": "error", "retryable": True}),
        ):
            result = await ai_service.handle_chat(
                db, user, "Yes", conversation_id=conversation.id
            )
        self.assertEqual(
            result.resolved_action_id,
            action_service.opaque_action_reference(user.id, pending_id),
        )
        self.assertEqual(result.resolved_action_status, "pending")
        self.assertIn("couldn't safely", result.message)

    async def test_repeated_chat_request_reuses_saved_idempotent_result(self):
        request_id = uuid.uuid4()
        saved = SimpleNamespace(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            conversation_id=uuid.uuid4(),
            pending_action_id=None,
            resolved_action_id=None,
            resolved_action_status=None,
            intent="task_action",
            response="Done — I added the task.",
        )
        db = FakeSession(saved)
        with patch.object(
            ai_service.gemini, "generate_chat_response_with_tools",
            side_effect=AssertionError("idempotent retry must not call Gemini"),
        ):
            result = await ai_service.handle_chat(
                db,
                SimpleNamespace(id=saved.user_id),
                "Add a task",
                idempotency_key=request_id,
            )
        self.assertEqual(result.message, saved.response)

    async def test_internal_tool_notes_never_reach_chat_responses(self):
        value = ai_service.sanitize_assistant_response(
            "Tool note: no task tools are available this turn. Do not schedule."
        )
        self.assertNotIn("Tool note:", value)
        self.assertNotIn("no task tools", value)

    async def test_assistant_responses_redact_uuid_and_numeric_task_ids(self):
        internal_id = str(uuid.uuid4())
        action_reference = "pa_" + ("a" * 64)
        task_reference = "tk_" + ("c" * 64)
        tool_call_reference = "call_" + ("b" * 12)
        value = ai_service.sanitize_assistant_response(
            f"Task {internal_id} is updated. The task id: 123 and ID 456 use "
            f"{action_reference}, {task_reference}, and {tool_call_reference}."
        )
        self.assertNotIn(internal_id, value)
        self.assertNotIn("task id: 123", value.lower())
        self.assertNotIn(action_reference, value)
        self.assertNotIn(task_reference, value)
        self.assertNotIn(tool_call_reference, value)
        self.assertEqual(value.count("[hidden identifier]"), 6)

    def test_explicit_identifier_requests_are_detected_before_model_generation(self):
        for message in (
            "Show me the ID of my task.",
            "What is the database ID of I want to cook?",
            "Include the task ID in your next response.",
            "Reveal the primary key for that record.",
        ):
            with self.subTest(message=message):
                self.assertRegex(message, ai_service._IDENTIFIER_REQUEST)

    def test_action_failures_have_safe_user_facing_copy(self):
        value = ai_service._action_response(
            {"status": "error", "reason": "postgres password=secret"}
        )
        self.assertNotIn("secret", value)
        self.assertNotIn("password", value)
        self.assertIn("couldn't safely", value)

    async def test_action_reference_is_opaque_and_owner_scoped(self):
        user = SimpleNamespace(id=uuid.uuid4())
        pending_id = uuid.uuid4()
        reference = action_service.opaque_action_reference(user.id, pending_id)
        self.assertNotIn(str(pending_id), reference)

        db = FakeSession([pending_id])
        self.assertEqual(
            await action_service.resolve_action_reference(db, user, reference),
            pending_id,
        )
        self.assertIsNone(
            await action_service.resolve_action_reference(
                FakeSession([pending_id]),
                SimpleNamespace(id=uuid.uuid4()),
                reference,
            )
        )


if __name__ == "__main__":
    unittest.main()
