"""
tasks/sms_tasks.py
Celery background tasks for sending SMS messages.

BUG FIX:
  send_sms_task() was calling send_sms(phone=phone, message=message)
  but send_sms() signature is send_sms(phone, otp) — keyword 'message'
  caused a TypeError on every background SMS task.
  Fixed to use send_sms(phone=phone, otp=message).
"""

import logging
from asgiref.sync import async_to_sync
from src.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="src.tasks.sms_tasks.send_sms_task")
def send_sms_task(phone: str, message: str):
    """Send a generic SMS message in the background."""
    try:
        from src.integrations.twilio import send_sms
        # FIX: was send_sms(phone=phone, message=message) — wrong keyword
        async_to_sync(send_sms)(phone=phone, otp=message)
        logger.info("SMS sent  phone=%s", phone)
    except Exception as e:
        logger.error("SMS failed  phone=%s  error=%s", phone, str(e))


@celery_app.task(name="src.tasks.sms_tasks.send_otp_sms_task")
def send_otp_sms_task(phone: str, otp: str):
    """Send OTP via SMS in the background."""
    try:
        from src.integrations.twilio import send_sms
        async_to_sync(send_sms)(phone=phone, otp=otp)
        logger.info("OTP SMS sent  phone=%s", phone)
    except Exception as e:
        logger.error("OTP SMS failed  phone=%s  error=%s", phone, str(e))


@celery_app.task(name="src.tasks.sms_tasks.cleanup_expired_otps")
def cleanup_expired_otps():
    """
    Periodic task — clean up expired OTP audit records from DB.
    Redis handles TTL automatically; this is for DB audit table only.
    """
    logger.info("Running OTP cleanup task")