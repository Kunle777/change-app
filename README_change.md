# Elvyn / change-app

This guide summarizes the feature work completed in this workspace during this chat, explains the main service boundaries, and records remaining verification and follow-up.

## Brain dumps and task conversion

- Users can save a brain dump, parse it into multiple possible tasks, check or uncheck suggestions, and add the selected suggestions.
- `POST /api/braindump/{dump_id}/parse` returns `{ "suggestions": [...] }`. Suggestions have a short title and low/medium/high priority. Parsing may include an optional recurrence rule only when repetition is explicit; it never infers reminder time. If no recurrence start date is explicitly given, conversion starts on the current date in the rule time zone.
- `POST /api/braindump/{dump_id}/convert` accepts `{ "suggestions": [...] }` and returns created tasks.
- `tasks.source_brain_dump_id` points to `brain_dumps.id` (`ON DELETE SET NULL`). Conversion locks the dump row and creates its selected tasks, task events, and converted marker within one transaction. A retry returns tasks already linked to the dump.

## Voice task creation

- Voice capture parses one spoken task into a title, priority, date, and time through `POST /api/tasks/parse-voice`.
- If a spoken time has passed today and no date was given, Home moves the reminder to tomorrow and tells the user. If an explicit date/time has passed, it keeps the task and due date but clears the reminder with an explanation.
- `/api/tasks/{task_id}/snooze` accepts an optional `snoozed_until`; older callers without a body retain the ten-minute snooze behavior.

## Recurring tasks

- New repeating tasks create a `task_series` rule and the first task occurrence together. Daily, weekly, and monthly rules support an interval, start date, local reminder time, IANA time zone, optional end date, and optional occurrence limit.
- Celery fills a 30-day occurrence window. Each generated occurrence is a normal `tasks` row with `series_id` and `occurrence_date`, so existing Home, Calendar, task actions, and event logging continue to use task records.
- A partial unique index on `(series_id, occurrence_date)` makes repeated or concurrent generation idempotent. Series rows are locked with `SKIP LOCKED`; old recurrence rows without a series remain supported by the legacy completion-based generator.
- The Home create-task form offers no repeat, daily, weekly, or monthly, with weekday selection for weekly. Brain Dump conversion also creates a series when the note explicitly asks for repetition. Task detail can stop a series and cancel its future pending occurrences. Changes to an entire series and per-occurrence exceptions are not implemented yet.
- Recurring reminders use the existing Expo local notification mechanism. Reconciliation runs whenever Home loads/synchronizes tasks and when the app returns to the foreground; it schedules only the existing 14-day local window. Series generation itself creates database tasks and never schedules phone notifications directly.

## Task reminder delivery

- Expo local notifications remain the primary offline-capable task reminder mechanism and carry `data.type = "task_reminder"` plus the task ID and reminder time.
- The existing FCM backend remains as fallback. Before sending, Celery checks for a matching `reminder_scheduled` event in the log or outbox. A confirmed local reminder suppresses FCM for that task/time, preventing two alerts. If FCM send fails, the reminder remains eligible for retry.
- Reminder reconciliation and sign-out cleanup target only tagged/mapped task notifications; other notification types are left alone. Notification-open and local-schedule signals are recorded through the authenticated task-event endpoint.

## Behavioral task events

`task_events` records `created`, `reminder_scheduled`, `reminder_opened`, `completed`, `not_now`, `rescheduled`, `cancelled`, `overdue`, and `deadline_changed`. It stores an optional task FK, required user FK, event time, insert time, and JSONB event metadata. `task_event_outbox` holds events durably until they are delivered. Both tables have partial unique indexes to prevent duplicate overdue events for the same task/deadline and duplicate reminder events for the same notification.

Event names are validated in Python with `TaskEventType` and stored as `VARCHAR(30)`, rather than a PostgreSQL enum. PostgreSQL does not constrain values in this column; event types should be added through the Python enum and reviewed before use.

Task actions enqueue events using a nested database savepoint with a 500 ms statement timeout. If enqueueing fails, only the savepoint is rolled back and the caller can still commit the task action. If it succeeds, the outbox row and action commit together. A Celery worker copies outbox rows into `task_events` and removes delivered rows in one transaction; failures leave the outbox entry for retry. This survives process restarts without allowing event logging to poison the task action transaction.

Server actions emit creation, completion, not-now/snooze, reschedule, deadline-change, and cancellation events. Brain-dump-created tasks and generated recurring occurrences also emit `created`. The client reports actual local reminder scheduling and notification opens through an authenticated task event route; these are deduplicated by Expo notification ID. Celery Beat drains the outbox, generates recurrence occurrences, and checks overdue tasks. Unique indexes and `FOR UPDATE SKIP LOCKED` make these jobs safe to retry and run on multiple workers.

If an outbox insert itself fails or times out, the task action proceeds without that event; this preserves the core failure-isolation rule. Once an event is in the outbox, delivery retries survive worker restarts. Monitor outbox size and age so persistent delivery failures are visible.

## Check-ins and prompt selection

- Morning/evening check-ins use the existing check-in endpoints and can save mood, a morning goal, evening goal status, and an optional reflection.
- Prompt text is in `frontend/data/prompts.ts`. `frontend/utils/elvynCheckInResponse.ts` selects a mood-aware daily prompt/response and exports a starting-task prompt helper.
- Daily selections remain stable during rerenders instead of changing on each component render.

## Daily activity streak

- Authenticated app startup/sign-in and foreground resume call `POST /api/users/activity` with the device's IANA time zone. The user row stores current streak, longest streak, last active local date, and the time zone used.
- A row lock and date comparison ensure repeated opens on one local calendar day count once. Returning the next day increments the streak; returning after a missed day starts the current streak at one and preserves the longest streak.
- The streak is independent of check-ins and Win Log entries. The older Win Log database/API remain for compatibility, but the screen is no longer linked from Home or the app navigation. Streak milestone/evolution data should stay separate from the mascot's neutral/supportive emotional variant; visual evolution tiers are not implemented yet.

## Appearance and navigation

- `ThemeProvider` stores the `system`, `light`, or `dark` choice in AsyncStorage. `useColors()` returns the corresponding palette, and React Navigation receives the resolved theme.
- The More tab includes Appearance and log out. Deferred destinations are marked "Coming soon"; the existing Settings screen remains reachable.
- The palette is applied to Appearance, More, Check-in, Brain Dump, Home, Task Detail, and the task row/action controls. Older screens such as Savings and account setup still need a broader visual pass for full dark-mode coverage.

## Apply backend migrations

Set `DATABASE_URL` or `SUPABASE_DB_URL` in `change-backend/.env`, then run from the repository root:

```bash
alembic upgrade head
```

Migration `c814d62a9f31` follows the task-event merge and adds `task_series`, occurrence linkage/uniqueness, and activity streak fields on users. All models are imported by `change-backend/alembic/env.py` so later autogenerate runs can discover them.

The backend requirements include Celery with its Redis transport extra, which the existing Celery app/Beat configuration requires. Set `REDIS_URL`, then run a Celery worker and Beat scheduler from `change-backend` in separate processes:

```bash
celery -A celery_app.celery_app worker --pool=solo
celery -A celery_app.celery_app beat
```

`--pool=solo` is suitable for the local Windows development environment; use the deployment's supported worker pool in production.

## Verify task events

After migrating and starting the app, create a task, complete one, reschedule one, open a reminder, and allow the Celery Beat overdue job to run. Then query:

```sql
select event_type, task_id, event_metadata, occurred_at, created_at
from task_events
where user_id = '<your user id>'
order by occurred_at desc
limit 20;
```

`occurred_at` is captured when the action is recorded; `created_at` is the database insertion time. For reminder fallback checks, compare each task's current reminder time to `event_metadata->>'reminder_time'` for `reminder_scheduled` in both the log and outbox.

## APK smoke checks

Use a physical Android device, apply migrations, and run the backend, Celery worker, and Beat scheduler.

1. Create a one-time task with a reminder a few minutes ahead. Confirm the tagged Expo local reminder fires once while the app is backgrounded.
2. Open that reminder. Confirm it launches the app and a single `reminder_opened` event reaches the outbox/log.
3. Reschedule, complete, cancel, and sign out with pending reminders. Confirm old local alerts are canceled and sign-out cleanup leaves non-task notifications alone.
4. With FCM configured, confirm a matching locally scheduled reminder suppresses the Celery FCM fallback. Then create a task on a client/device that has no local schedule and confirm FCM is attempted as fallback.
5. Create daily, weekly-on-selected-days, and monthly tasks. Confirm their first occurrence appears in Home and Calendar, Beat fills up to the 30-day window, and each occurrence appears only once with the intended local date/time.
6. Stop a series from Task Detail. Confirm future pending occurrences disappear, their local reminders reconcile away, and the current/completed occurrence remains in history.
7. Open the app several times on one local date and confirm current streak increments once. Open after the next local date to confirm it increments by one; after a missed date confirm it resets to one and the longest streak remains.
8. Toggle Check-ins off and add Win Log entries through any retained API. Confirm neither changes the activity streak.

The backend tests and migration have not been run in this environment; use the verification commands below before treating this checklist as passed.

## Verification status and next steps

- Frontend `tsc --noEmit` and `git diff --check` pass.
- Backend unit tests are in `change-backend/tests/test_task_event_service.py`; they cover outbox event payloads, simulated savepoint failure isolation, event uniqueness metadata, and overdue retry filtering. They use a modeled session and are not a substitute for PostgreSQL integration tests.
- Run those tests from `change-backend` with `python -m unittest discover -s tests`.
- Python and Alembic were not available in the editing environment, so the backend tests and `alembic upgrade head` could not be run here. Run them in the configured backend environment before relying on the new migration or event path.
- Consider an integration test against PostgreSQL to verify the migration, savepoint recovery, outbox retry, concurrent overdue deduplication, and reminder-open uniqueness end to end.
- There is no user-facing task event history yet. Dark mode does not recolor every legacy screen.
