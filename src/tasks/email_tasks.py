"""
tasks/email_tasks.py
Background tasks for email sending.
"""

import logging
from src.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="src.tasks.email_tasks.send_email_task")
def send_email_task(to: str, subject: str, body: str):
    """Send a plain email in the background."""
    try:
        import asyncio
        from src.integrations.sendgrid import send_email
        asyncio.run(send_email(to=to, subject=subject, body=body))
        logger.info("Email sent to=%s subject='%s'", to, subject)
    except Exception as e:
        logger.error("Email failed to=%s error=%s", to, str(e))


@celery_app.task(name="src.tasks.email_tasks.send_otp_email_task")
def send_otp_email_task(to: str, otp: str, purpose: str = "verification"):
    """Send OTP via email in the background."""
    try:
        import asyncio
        from src.integrations.sendgrid import send_otp_email
        asyncio.run(send_otp_email(to=to, otp=otp, purpose=purpose))
        logger.info("OTP email sent to=%s purpose=%s", to, purpose)
    except Exception as e:
        logger.error("OTP email failed to=%s error=%s", to, str(e))


@celery_app.task(name="src.tasks.email_tasks.send_welcome_email_task")
def send_welcome_email_task(to: str, name: str):
    """Send welcome email to new users."""
    try:
        import asyncio
        from src.integrations.sendgrid import send_email
        asyncio.run(send_email(
            to=to,
            subject="Welcome to AP Tourism!",
            body=(
                f"Hi {name},\n\n"
                "Welcome to AP Tourism — your guide to Andhra Pradesh's temples and destinations.\n\n"
                "Start exploring at https://aptourism.ap.gov.in\n\n"
                "— AP Tourism Team"
            )
        ))
    except Exception as e:
        logger.error("Welcome email failed to=%s error=%s", to, str(e))