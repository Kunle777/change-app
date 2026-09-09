import ssl
from celery import Celery
from dotenv import load_dotenv
import os
from celery.schedules import crontab


load_dotenv()

celery_app = Celery(
    "change",
    broker=os.getenv("REDIS_URL"),
    backend=os.getenv("REDIS_URL"),
    include=["app.tasks_celery"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Africa/Lagos",
    enable_utc=True,
    broker_use_ssl={"ssl_cert_reqs": ssl.CERT_REQUIRED},
    redis_backend_use_ssl={
        "ssl_cert_reqs": ssl.CERT_REQUIRED,
    }
)

celery_app.conf.beat_schedule = {
    "check-reminders-every-minute": {
        "task": "app.tasks_celery.check_reminders",
        "schedule": crontab(minute="*"),
    },
    "spawn-recurring-tasks-hourly": {
        "task": "app.tasks_celery.spawn_recurring_task_job",
        "schedule": crontab(minute=0, hour="*"),
    },
        # ... your existing check_reminders entry stays as-is ...
    "process-matured-vaults": {
        "task": "app.savings.tasks_celery.process_matured_vaults",
        "schedule": crontab(minute="0"),  # hourly, on the hour
    },
}


