import ssl
from celery import Celery
from dotenv import load_dotenv
import os
from celery.schedules import crontab


load_dotenv()

REDIS_URL = os.getenv("REDIS_URL")
# Upstash (production) uses rediss:// and needs TLS options; a local redis://
# server must not receive them or the connection fails.
_USE_TLS = bool(REDIS_URL and REDIS_URL.startswith("rediss://"))

celery_app = Celery(
    "change",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks_celery", "app.memory.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Africa/Lagos",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
)

if _USE_TLS:
    celery_app.conf.broker_use_ssl = {"ssl_cert_reqs": ssl.CERT_REQUIRED}
    celery_app.conf.redis_backend_use_ssl = {"ssl_cert_reqs": ssl.CERT_REQUIRED}

celery_app.conf.beat_schedule = {
    "check-reminders-every-minute": {
        "task": "app.tasks_celery.check_reminders",
        "schedule": crontab(minute="*"),
    },
    "spawn-recurring-tasks-hourly": {
        "task": "app.tasks_celery.spawn_recurring_task_job",
        "schedule": crontab(minute=0, hour="*"),
    },
    "record-overdue-task-events": {
        "task": "app.tasks_celery.record_overdue_task_events_job",
        "schedule": crontab(minute="*"),
    },
    "deliver-task-event-outbox": {
        "task": "app.tasks_celery.deliver_task_event_outbox_job",
        "schedule": crontab(minute="*"),
    },
    "sweep-memory-index": {
        "task": "app.memory.tasks.sweep_memory_index_job",
        "schedule": crontab(minute="*/15"),
    },
}

