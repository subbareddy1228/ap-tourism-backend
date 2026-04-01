"""
integrations/sendgrid.py
Email sending integration using SendGrid API.

Required .env variables:

SENDGRID_API_KEY
SENDGRID_FROM_EMAIL
SENDGRID_FROM_NAME
"""

import logging
from typing import Optional

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from src.core.config import settings

logger = logging.getLogger(__name__)

_MOCK_MODE = not settings.SENDGRID_API_KEY


# ─────────────────────────────────────────────
# CORE EMAIL FUNCTION
# ─────────────────────────────────────────────
async def send_email(
    to: str,
    subject: str,
    body: str,
    html: Optional[str] = None,
) -> bool:
    """
    Send email via SendGrid.

    Returns True if success, False if failed.
    """

    if _MOCK_MODE:
        logger.warning("SENDGRID MOCK MODE — email not sent")
        logger.info("TO: %s", to)
        logger.info("SUBJECT: %s", subject)
        logger.info("BODY: %s", body)
        return True

    try:
        message = Mail(
            from_email=settings.SENDGRID_FROM_EMAIL,
            to_emails=to,
            subject=subject,
            plain_text_content=body,
            html_content=html or body,
        )

        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(message)

        logger.info(
            "Email sent to=%s status=%s",
            to,
            response.status_code
        )

        return True

    except Exception as e:
        logger.error("SendGrid email failed to=%s error=%s", to, str(e))
        return False


# ─────────────────────────────────────────────
# OTP EMAIL
# ─────────────────────────────────────────────
async def send_otp_email(
    to: str,
    otp: str,
    purpose: str = "verification",
) -> bool:

    subject = f"Your AP Tourism {purpose} code"

    body = (
        f"Your verification code is: {otp}\n\n"
        f"This code expires in {settings.OTP_EXPIRE_SECONDS // 60} minutes.\n"
        f"Do not share this code with anyone.\n\n"
        f"— AP Tourism Team"
    )

    html = f"""
    <h2>AP Tourism Verification</h2>
    <p>Your OTP code:</p>
    <h1>{otp}</h1>
    <p>This code expires in {settings.OTP_EXPIRE_SECONDS // 60} minutes.</p>
    """

    return await send_email(to, subject, body, html)


# ─────────────────────────────────────────────
# BOOKING CONFIRMATION EMAIL
# ─────────────────────────────────────────────
async def send_booking_confirmation(
    to: str,
    booking_number: str,
    amount: float,
) -> bool:

    subject = f"Booking Confirmed — {booking_number}"

    body = (
        f"Your booking {booking_number} has been confirmed.\n"
        f"Total Amount: ₹{amount:.2f}\n\n"
        f"Thank you for choosing AP Tourism!\n"
        f"— AP Tourism Team"
    )

    html = f"""
    <h2>Booking Confirmed</h2>
    <p>Your booking <b>{booking_number}</b> has been confirmed.</p>
    <p>Total Amount: <b>₹{amount:.2f}</b></p>
    <p>Thank you for choosing AP Tourism.</p>
    """

    return await send_email(to, subject, body, html)


# ─────────────────────────────────────────────
# PASSWORD RESET EMAIL
# ─────────────────────────────────────────────
async def send_password_reset(
    to: str,
    otp: str,
) -> bool:

    subject = "Reset your AP Tourism password"

    body = (
        f"Your password reset code is: {otp}\n\n"
        f"This code expires in {settings.OTP_EXPIRE_SECONDS // 60} minutes.\n"
        f"If you did not request this, ignore this email.\n\n"
        f"— AP Tourism Team"
    )

    html = f"""
    <h2>Password Reset</h2>
    <p>Your reset OTP:</p>
    <h1>{otp}</h1>
    <p>This code expires in {settings.OTP_EXPIRE_SECONDS // 60} minutes.</p>
    """

    return await send_email(to, subject, body, html)