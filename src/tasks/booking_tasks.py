"""
tasks/booking_tasks.py
Background tasks for the Booking module.
"""

import logging
from src.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="src.tasks.booking_tasks.send_booking_confirmation")
def send_booking_confirmation(booking_id: str, user_email: str, booking_number: str, amount: float):
    """Send booking confirmation email after successful payment."""
    try:
        import asyncio
        from src.integrations.sendgrid import send_booking_confirmation as send_email
        asyncio.run(send_email(
            to=user_email,
            booking_number=booking_number,
            amount=amount,
        ))
        logger.info("Booking confirmation sent booking_id=%s", booking_id)
    except Exception as e:
        logger.error("Booking confirmation failed booking_id=%s error=%s", booking_id, str(e))


@celery_app.task(name="src.tasks.booking_tasks.send_booking_reminders")
def send_booking_reminders():
    """
    Periodic task — send reminders for upcoming bookings (24 hours before).
    Run every hour via celery beat.
    """
    logger.info("Running booking reminders task")
    # TODO: Query bookings starting tomorrow and send reminders


@celery_app.task(name="src.tasks.booking_tasks.send_cancellation_email")
def send_cancellation_email(booking_id: str, user_email: str, booking_number: str):
    """Send booking cancellation confirmation email."""
    try:
        import asyncio
        from src.integrations.sendgrid import send_email
        asyncio.run(send_email(
            to=user_email,
            subject=f"Booking Cancelled — {booking_number}",
            body=f"Your booking {booking_number} has been cancelled.\n\nFor refund queries contact support.\n\n— AP Tourism Team"
        ))
        logger.info("Cancellation email sent booking_id=%s", booking_id)
    except Exception as e:
        logger.error("Cancellation email failed booking_id=%s error=%s", booking_id, str(e))