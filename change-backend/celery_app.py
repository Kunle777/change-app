import ssl
from celery import Celery
from dotenv import load_dotenv
import os

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
    redis_backend_use_ssl={
        "ssl_cert_reqs": ssl.CERT_NONE,
    },
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    "check-reminders-every-minute": {
        "task": "app.tasks_celery.check_reminders",
        "schedule": 60.0,
    },
}