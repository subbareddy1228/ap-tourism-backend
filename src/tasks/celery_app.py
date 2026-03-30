"""
tasks/celery_app.py
Celery application configuration.
Used for background tasks: email sending, SMS, booking reminders, reports.

Note: Celery requires Redis as broker (already configured in .env).
Start worker with:
    celery -A src.tasks.celery_app worker --loglevel=info
"""

from celery import Celery
from src.core.config import settings

celery_app = Celery(
    "ap_tourism",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "src.tasks.booking_tasks",
        "src.tasks.email_tasks",
        "src.tasks.sms_tasks",
        "src.tasks.notification_tasks",
        "src.tasks.report_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "src.tasks.booking_tasks.*":      {"queue": "bookings"},
        "src.tasks.email_tasks.*":        {"queue": "emails"},
        "src.tasks.sms_tasks.*":          {"queue": "sms"},
        "src.tasks.notification_tasks.*": {"queue": "notifications"},
        "src.tasks.report_tasks.*":       {"queue": "reports"},
    },
    beat_schedule={
        "send-booking-reminders-hourly": {
            "task":     "src.tasks.booking_tasks.send_booking_reminders",
            "schedule": 3600.0,
        },
        "cleanup-expired-otps-daily": {
            "task":     "src.tasks.sms_tasks.cleanup_expired_otps",
            "schedule": 86400.0,
        },
    },
)