"""
integrations/email.py
Async email sending via Gmail SMTP (aiosmtplib).

Required .env variables:
    GMAIL_SENDER       — your Gmail address (e.g. noreply@aptourism.in)
    GMAIL_APP_PASSWORD — Gmail App Password (not your account password)
                         Generate at: myaccount.google.com/apppasswords

Usage:
    from src.integrations.email import send_email_otp
    await send_email_otp("user@example.com", "123456")
"""

import logging
import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.core.config import settings

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def _build_otp_email(otp: str, purpose: str) -> tuple[str, str]:
    purpose_labels = {
        "verify_email":    ("Verify your email address", "verify your email address"),
        "forgot_password": ("Reset your password",       "reset your password"),
        "register":        ("Complete your registration","complete your registration"),
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
              Use the OTP below to {action}. It expires in <strong>10 minutes</strong> and can only be used once.
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


async def send_email(to: str, subject: str, html_body: str) -> bool:
    """Send HTML email via Gmail SMTP (async). Returns True on success, False on failure."""
    if not settings.GMAIL_SENDER or not settings.GMAIL_APP_PASSWORD:
        logger.warning("Email not configured — GMAIL_SENDER or GMAIL_APP_PASSWORD missing")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"AP Tourism <{settings.GMAIL_SENDER}>"
    msg["To"]      = to
    msg.attach(MIMEText(html_body, "html"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=settings.GMAIL_SENDER,
            password=settings.GMAIL_APP_PASSWORD,
            start_tls=True,
        )
        logger.info("Email sent to=%s subject=%r", to, subject)
        return True
    except Exception as exc:
        logger.error("Email send failed to=%s error=%s", to, exc)
        return False


async def send_email_otp(to: str, otp: str, purpose: str = "verify_email") -> bool:
    """Send an OTP email for the given purpose."""
    subject, html = _build_otp_email(otp, purpose)
    return await send_email(to, subject, html)