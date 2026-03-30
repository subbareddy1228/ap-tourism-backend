"""
integrations/sendgrid.py
Email sending integration.
Uses Gmail SMTP (configured in .env) — no SendGrid account needed.
Falls back to console log in dev mode if credentials not set.

Required .env:
    GMAIL_SENDER=yourmail@gmail.com
    GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx  (Gmail App Password)
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from src.core.config import settings

logger = logging.getLogger(__name__)

_MOCK_MODE = not settings.GMAIL_SENDER or not settings.GMAIL_APP_PASSWORD


async def send_email(
    to:       str,
    subject:  str,
    body:     str,
    html:     Optional[str] = None,
) -> bool:
    """
    Send an email via Gmail SMTP.

    Args:
        to:      Recipient email address.
        subject: Email subject line.
        body:    Plain text body.
        html:    Optional HTML body (falls back to plain text).

    Returns:
        True on success, False on failure (never raises).
    """
    if _MOCK_MODE:
        logger.info(
            "EMAIL mock mode — not sent. to=%s subject='%s'",
            to, subject
        )
        logger.info("EMAIL BODY: %s", body)
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = settings.GMAIL_SENDER
        msg["To"]      = to

        msg.attach(MIMEText(body, "plain"))
        if html:
            msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.GMAIL_SENDER, settings.GMAIL_APP_PASSWORD)
            server.sendmail(settings.GMAIL_SENDER, to, msg.as_string())

        logger.info("Email sent to=%s subject='%s'", to, subject)
        return True

    except Exception as e:
        logger.error("Email failed to=%s error=%s", to, str(e))
        return False


async def send_otp_email(to: str, otp: str, purpose: str = "verification") -> bool:
    """Send OTP code via email."""
    subject = f"Your AP Tourism {purpose} code"
    body = (
        f"Your verification code is: {otp}\n\n"
        f"This code expires in {settings.OTP_EXPIRE_SECONDS // 60} minutes.\n"
        f"Do not share this code with anyone.\n\n"
        f"— AP Tourism Team"
    )
    return await send_email(to=to, subject=subject, body=body)


async def send_booking_confirmation(
    to:             str,
    booking_number: str,
    amount:         float,
) -> bool:
    """Send booking confirmation email."""
    subject = f"Booking Confirmed — {booking_number}"
    body = (
        f"Your booking {booking_number} has been confirmed.\n"
        f"Total Amount: ₹{amount:.2f}\n\n"
        f"Thank you for choosing AP Tourism!\n"
        f"— AP Tourism Team"
    )
    return await send_email(to=to, subject=subject, body=body)


async def send_password_reset(to: str, otp: str) -> bool:
    """Send password reset OTP."""
    subject = "Reset your AP Tourism password"
    body = (
        f"Your password reset code is: {otp}\n\n"
        f"This code expires in {settings.OTP_EXPIRE_SECONDS // 60} minutes.\n"
        f"If you did not request this, ignore this email.\n\n"
        f"— AP Tourism Team"
    )
    return await send_email(to=to, subject=subject, body=body)