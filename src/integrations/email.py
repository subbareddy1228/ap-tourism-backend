"""
integrations/email.py
Async email sending via SendGrid API.

Required .env variables:
    SENDGRID_API_KEY       — Your SendGrid API key (starts with SG.)
    SENDGRID_FROM_EMAIL    — Verified sender email in SendGrid
    SENDGRID_FROM_NAME     — Sender display name (default: AP Tourism)

Usage:
    from src.integrations.email import send_email_otp
    await send_email_otp("user@example.com", "123456", purpose="verify_email")
"""

import logging
from typing import Optional

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

from src.core.config import settings

logger = logging.getLogger(__name__)

# ── Mock mode if SendGrid not configured ─────────────────────
_MOCK_MODE = not settings.SENDGRID_API_KEY or not settings.SENDGRID_FROM_EMAIL


# ── OTP Email HTML Template ──────────────────────────────────

def _build_otp_html(otp: str, purpose: str) -> tuple[str, str]:
    """Build subject and HTML body for OTP email."""
    purpose_labels = {
        "verify_email":    ("Verify your email address",    "verify your email address"),
        "forgot_password": ("Reset your AP Tourism password", "reset your password"),
        "register":        ("Complete your registration",   "complete your registration"),
    }
    subject, action = purpose_labels.get(
        purpose,
        ("Your AP Tourism OTP", "complete your action")
    )

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f4f4f4;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:40px 0;">
      <table width="520" cellpadding="0" cellspacing="0"
             style="background:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
        <tr>
          <td style="background:#1a56db;padding:28px 40px;">
            <h1 style="margin:0;color:#ffffff;font-size:22px;font-weight:600;">AP Travel &amp; Temple Tourism</h1>
          </td>
        </tr>
        <tr>
          <td style="padding:36px 40px;">
            <p style="margin:0 0 16px;color:#374151;font-size:15px;line-height:1.6;">
              Use the OTP below to {action}. It expires in <strong>5 minutes</strong> and can only be used once.
            </p>
            <div style="margin:28px 0;text-align:center;">
              <span style="display:inline-block;background:#f0f4ff;border:2px dashed #1a56db;
                           border-radius:8px;padding:18px 40px;font-size:36px;font-weight:700;
                           letter-spacing:12px;color:#1a56db;">{otp}</span>
            </div>
            <p style="margin:0;color:#6b7280;font-size:13px;line-height:1.6;">
              If you did not request this, please ignore this email. Your account is safe.
            </p>
          </td>
        </tr>
        <tr>
          <td style="background:#f9fafb;padding:20px 40px;border-top:1px solid #e5e7eb;">
            <p style="margin:0;color:#9ca3af;font-size:12px;">
              AP Travel &amp; Temple Tourism Platform &nbsp;|&nbsp; This is an automated message, please do not reply.
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

    return subject, html


# ── Core Send Function ────────────────────────────────────────

async def send_email(
    to:      str,
    subject: str,
    html_body: str,
    plain_body: Optional[str] = None,
) -> bool:
    """
    Send HTML email via SendGrid API.

    Returns True on success, False on failure (never raises).
    In mock mode (no API key), logs the email and returns True.
    """
    if _MOCK_MODE:
        logger.warning(
            "SENDGRID MOCK MODE — email not sent. to=%s subject=%r",
            to, subject
        )
        logger.info("OTP would be sent to: %s", to)
        return True

    try:
        from_email = Email(
            email=settings.SENDGRID_FROM_EMAIL,
            name=settings.SENDGRID_FROM_NAME or "AP Tourism",
        )
        to_email = To(to)

        message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject=subject,
        )
        message.add_content(Content("text/html", html_body))
        if plain_body:
            message.add_content(Content("text/plain", plain_body))

        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(message)

        if response.status_code in (200, 201, 202):
            logger.info(
                "SendGrid email sent to=%s subject=%r status=%d",
                to, subject, response.status_code
            )
            return True
        else:
            logger.error(
                "SendGrid email failed to=%s status=%d body=%s",
                to, response.status_code, response.body
            )
            return False

    except Exception as e:
        logger.error("SendGrid email failed to=%s error=%s", to, str(e))
        return False


# ── OTP Email ─────────────────────────────────────────────────

async def send_email_otp(
    to:      str,
    otp:     str,
    purpose: str = "verify_email",
) -> bool:
    """
    Send OTP verification email via SendGrid.

    Args:
        to:      Recipient email address
        otp:     6-digit OTP code
        purpose: verify_email | forgot_password | register

    Returns:
        True on success, False on failure
    """
    subject, html = _build_otp_html(otp, purpose)
    plain = (
        f"Your AP Tourism OTP is: {otp}\n\n"
        f"This code expires in 5 minutes.\n"
        f"Do not share this code with anyone.\n\n"
        f"— AP Tourism Team"
    )
    return await send_email(to=to, subject=subject, html_body=html, plain_body=plain)


# ── Booking Confirmation Email ────────────────────────────────

async def send_booking_confirmation(
    to:             str,
    booking_number: str,
    amount:         float,
) -> bool:
    """Send booking confirmation email."""
    subject = f"Booking Confirmed — {booking_number}"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:520px;margin:0 auto;padding:20px;">
      <h2 style="color:#1a56db;">Booking Confirmed ✓</h2>
      <p>Your booking <strong>{booking_number}</strong> has been confirmed.</p>
      <p>Total Amount: <strong>₹{amount:.2f}</strong></p>
      <p>Thank you for choosing AP Tourism!</p>
    </div>
    """
    plain = f"Booking {booking_number} confirmed. Amount: ₹{amount:.2f}. Thank you!"
    return await send_email(to=to, subject=subject, html_body=html, plain_body=plain)