# Change Notification Architecture

## Overview

Change currently has two notification systems:

- **Local notifications:** scheduled directly on the user's phone with `expo-notifications`.
- **Firebase Cloud Messaging (FCM):** sent remotely by the backend through Firebase Admin, with Celery Beat and a Celery worker coordinating the job.

They are different delivery systems. Firebase is not the same as a local notification. Firebase transports a remote message to the device; Android or iOS ultimately displays it.

## Local notification flow

For a task created in `HomeScreen`:

```text
User chooses a date and time
        |
        v
The app saves the task through the API
        |
        v
The app schedules an OS notification with expo-notifications
        |
        v
Android/iOS stores the trigger and fires it at that time
```

After scheduling, the phone owns the trigger. The backend, Redis, Celery, and internet are not needed when the notification fires.

Local reminders:

- Work offline after they have been scheduled.
- Require a physical device, not an emulator/simulator.
- Require notification permission.
- Require a native build containing `expo-notifications`.
- Require an Android notification channel and Android 13+ notification permission.
- Store their notification ID in AsyncStorage so they can be cancelled or rescheduled.
- Are cancelled when a task is completed.
- Are replaced when a task is snoozed.
- Are ignored when the date is invalid or already in the past.

## Firebase remote notification flow

The backend path is:

```text
Celery Beat runs every minute
        |
        v
The Celery worker runs check_reminders
        |
        v
The database query finds reminder_time <= now
        |
        v
The backend reads the user's fcm_token
        |
        v
Firebase Admin sends the message to FCM
        |
        v
FCM delivers it to the device over the internet
```

The remote path requires all of these:

- A valid, reachable Redis broker.
- Celery worker running.
- Celery Beat running.
- Database connectivity.
- `FIREBASE_CREDENTIALS_PATH` pointing to the Firebase service-account file.
- A current FCM token saved for the user.
- Internet access at delivery time.

The worker and Beat are separate processes:

```bash
# API
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# Worker
python -m celery -A celery_app:celery_app worker --pool=solo --loglevel=info

# Beat
python -m celery -A celery_app:celery_app beat --loglevel=info
```

Run those commands from `change-backend` with its virtual environment active. The root-level module is `celery_app`, not `app.celery_app`.

## Do they clash?

They do not overwrite each other's notification IDs or schedules. Local scheduling is owned by Android/iOS, while FCM delivery is owned by Firebase and the operating system.

However, the current task flow can produce duplicates:

1. `HomeScreen` schedules a local reminder immediately.
2. The task is stored with `reminder_time` in the database.
3. Celery Beat later finds that same reminder.
4. FCM sends another message if the user has an FCM token.

That means one task can create two notifications. They may arrive close together, but the local notification is normally more exact while the FCM one waits for the next backend check and network delivery.

This is duplicate delivery, not a database conflict.

## Will the UI look the same?

Both may appear in the phone's notification tray with similar content, such as:

- Title: `Task Reminder`
- Body: the task title
- Sound enabled

They are not guaranteed to look or behave identically. Their appearance depends on:

- The Android notification channel.
- The FCM payload.
- Whether the app is foregrounded, backgrounded, or closed.
- Android/iOS notification grouping and ranking.
- Battery optimization and user notification settings.
- Network availability for FCM.

The local path uses the app's `expo-notifications` handler and channel. The remote path uses Firebase delivery and the platform's remote-notification handling. The operating system renders both, but it can display them differently.

## What should own a task reminder?

Use the system based on where the trigger is known:

| Situation | Recommended owner |
|---|---|
| Exact task time is known when the task is created | Local notification |
| User snoozes a task to a known future time | Local notification |
| Server receives a payment webhook | FCM |
| Another user performs an action | FCM |
| A server-side threshold or calculation is reached | FCM |
| A reminder must reach several logged-in devices | FCM or an explicit multi-device design |

For ordinary task reminders, local notifications are the more resilient primary owner because they work without internet at fire-time. FCM is the correct owner for events that the phone could not know about in advance.

## Recommended policy for Change

Choose one owner for ordinary task reminders. The simplest policy is:

- Keep local scheduling for task creation and snooze.
- Use FCM for server-originated events.
- Do not send the same ordinary task reminder through both paths.

An alternative backend-only policy is possible, but it requires Redis, Celery, Beat, Firebase credentials, an FCM token, and network access every time. It is less resilient for a known task time.

If both paths are deliberately needed in the future, make that explicit with a field such as:

```text
notification_mode = local | remote | both
```

## Testing local reminders

1. Use a physical phone.
2. Rebuild/reinstall the native app after native permission changes.
3. Grant notification permission.
4. Create a task 2-5 minutes in the future.
5. Put the app in the background or lock the phone.
6. Disable Wi-Fi after the task is saved.
7. Confirm that the local reminder appears.

Celery and the backend do not need to be running for this local-only test.

## Testing Firebase reminders

1. Start the API.
2. Start the worker and confirm it reports `Connected` to Redis.
3. Start Beat and confirm it reports `beat: Starting...`.
4. Confirm the user's FCM token exists and is current.
5. Create a task with a future reminder time.
6. Keep the phone online.
7. Wait for the next minute check plus network delay.
8. Inspect the worker log for the reminder check and FCM result.

If the phone is offline at delivery time, FCM cannot behave like a local notification. It depends on network access and Firebase/OS delivery behavior.

## Recent backend event-loop fix

Celery invokes the async reminder code with `asyncio.run()`. That creates and closes an event loop for each task invocation. SQLAlchemy's default async connection pool could then reuse an asyncpg connection created by a previous, already-closed loop.

The symptom was:

```text
RuntimeError: Event loop is closed
```

The backend engine now uses SQLAlchemy's `NullPool` in `app/database.py`. Connections are not reused across Celery's separate event loops. The reminder coroutine was also run twice in separate loops successfully after the change.

## Operational configuration

Celery expects a direct Redis URL, not a shell command:

```env
REDIS_URL=rediss://default:<password>@<upstash-host>:6379
FIREBASE_CREDENTIALS_PATH=firebase-credentials.json
```

The Firebase service-account file and all values in `.env` are sensitive. They should not be committed or shared. Any credentials that have been exposed should be rotated.

## Bottom line

- **Local:** device-owned, exact, offline-capable, best for known task times.
- **FCM:** server-owned, network-dependent, best for events discovered later.
- They do not technically clash, but both active for the same task can produce two visible notifications.
- For one notification per ordinary task reminder, choose a single owner.
