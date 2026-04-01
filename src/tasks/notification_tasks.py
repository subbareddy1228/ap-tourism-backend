"""
tasks/notification_tasks.py
Background tasks for push notifications via Firebase.
"""

import logging
from asgiref.sync import async_to_sync
from src.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="src.tasks.notification_tasks.send_push_task")
def send_push_task(fcm_token: str, title: str, body: str, data: dict = None):
    """Send push notification to a single device."""
    try:
        from src.integrations.firebase import send_push
        async_to_sync(send_push)(
            fcm_token=fcm_token,
            title=title,
            body=body,
            data=data or {},
        )
        logger.info("Push notification sent title='%s'", title)
    except Exception as e:
        logger.error("Push notification failed error=%s", str(e))


@celery_app.task(name="src.tasks.notification_tasks.send_multicast_task")
def send_multicast_task(fcm_tokens: list, title: str, body: str, data: dict = None):
    """Send push notification to multiple devices."""
    try:
        from src.integrations.firebase import send_multicast
        result = async_to_sync(send_multicast)(
            fcm_tokens=fcm_tokens,
            title=title,
            body=body,
            data=data or {},
        )
        logger.info("Multicast push sent title='%s' sent=%d failed=%d",
                    title, result["sent"], result["failed"])
    except Exception as e:
        logger.error("Multicast push failed error=%s", str(e))


@celery_app.task(name="src.tasks.notification_tasks.send_booking_push")
def send_booking_push(fcm_token: str, booking_number: str, status: str):
    """Send booking status update push notification."""
    title = "Booking Update"
    body  = f"Your booking {booking_number} is now {status}."
    send_push_task.delay(fcm_token=fcm_token, title=title, body=body, data={
        "booking_number": booking_number,
        "status": status,
        "type": "booking_update",
    })
    