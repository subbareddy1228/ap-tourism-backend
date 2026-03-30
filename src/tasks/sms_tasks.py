"""
tasks/sms_tasks.py
Background tasks for SMS sending.
"""

import logging
from src.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="src.tasks.sms_tasks.send_sms_task")
def send_sms_task(phone: str, message: str):
    """Send SMS in the background."""
    try:
        import asyncio
        from src.integrations.twilio import send_sms
        asyncio.run(send_sms(phone=phone, message=message))
        logger.info("SMS sent phone=%s", phone)
    except Exception as e:
        logger.error("SMS failed phone=%s error=%s", phone, str(e))


@celery_app.task(name="src.tasks.sms_tasks.send_otp_sms_task")
def send_otp_sms_task(phone: str, otp: str):
    """Send OTP via SMS in the background."""
    try:
        import asyncio
        from src.integrations.twilio import send_sms
        message = f"Your AP Tourism OTP is: {otp}. Valid for 5 minutes. Do not share."
        asyncio.run(send_sms(phone=phone, message=message))
        logger.info("OTP SMS sent phone=%s", phone)
    except Exception as e:
        logger.error("OTP SMS failed phone=%s error=%s", phone, str(e))


@celery_app.task(name="src.tasks.sms_tasks.cleanup_expired_otps")
def cleanup_expired_otps():
    """
    Periodic task — clean up expired OTP audit records from DB.
    Run daily via celery beat.
    """
    logger.info("Running OTP cleanup task")
    # Redis handles TTL automatically — this is for DB audit table cleanup