"""
integrations/email.py
Async email sending via SendGrid API
"""

import logging
from typing import Optional

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content, ReplyTo

from src.core.config import settings

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# MOCK MODE
# ─────────────────────────────────────────────
MOCK_MODE = not settings.SENDGRID_API_KEY or not settings.SENDGRID_FROM_EMAIL

if MOCK_MODE:
    logger.warning("SendGrid not configured. Email service running in MOCK MODE.")


# ─────────────────────────────────────────────
# OTP EMAIL TEMPLATE
# ─────────────────────────────────────────────

def _build_otp_html(otp: str, purpose: str) -> tuple[str, str]:

    purpose_labels = {
        "verify_email": ("Your AP Tourism email verification code", "verify your email address"),
        "forgot_password": ("Reset your AP Tourism password", "reset your password"),
        "register": ("Complete your AP Tourism registration", "complete your registration"),
    }

    subject, action = purpose_labels.get(
        purpose,
        ("Your AP Tourism verification code", "complete your action"),
    )

    html = f"""
    <html>
    <body style="font-family:Arial;padding:20px;background:#f4f4f4;">
        <div style="max-width:520px;margin:auto;background:white;padding:30px;border-radius:8px;">
            <h2 style="color:#1a56db;">AP Travel & Temple Tourism</h2>

            <p>Hello,</p>

            <p>
                Thank you for using <b>AP Tourism</b>.
            </p>

            <p>
                Use the verification code below to <b>{action}</b>.
                This code will expire in <b>5 minutes</b>.
            </p>

            <div style="text-align:center;margin:30px 0;">
                <span style="font-size:36px;font-weight:bold;color:#1a56db;">
                    {otp}
                </span>
            </div>

            <p style="font-size:14px;">
                If you did not request this email, please ignore it.
            </p>

            <p style="font-size:12px;color:#777;">
                — AP Tourism Team
            </p>
        </div>
    </body>
    </html>
    """

    return subject, html


# ─────────────────────────────────────────────
# CORE EMAIL FUNCTION
# ─────────────────────────────────────────────

async def send_email(
    to: str,
    subject: str,
    html_body: str,
    plain_body: Optional[str] = None,
) -> bool:

    if MOCK_MODE:
        logger.warning("MOCK MODE → Email not sent. to=%s subject=%s", to, subject)
        return True

    try:

        from_email = Email(
            email=settings.SENDGRID_FROM_EMAIL,
            name=settings.SENDGRID_FROM_NAME or "AP Tourism",
        )

        message = Mail(
            from_email=from_email,
            to_emails=To(to),
            subject=subject,
        )

        message.reply_to = ReplyTo(settings.SENDGRID_FROM_EMAIL)

        message.add_content(Content("text/html", html_body))

        if plain_body:
            message.add_content(Content("text/plain", plain_body))

        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)

        logger.info("Sending email to %s via SendGrid", to)

        response = sg.send(message)

        logger.info("SendGrid response status=%s", response.status_code)

        if response.status_code in (200, 201, 202):
            logger.info("Email successfully sent to %s", to)
            return True

        logger.error(
            "SendGrid error → status=%s body=%s",
            response.status_code,
            response.body,
        )
        return False

    except Exception as e:
        logger.exception("SendGrid email sending failed: %s", str(e))
        return False


# ─────────────────────────────────────────────
# SEND OTP EMAIL
# ─────────────────────────────────────────────

async def send_email_otp(
    to: str,
    otp: str,
    purpose: str = "verify_email",
) -> bool:

    subject, html = _build_otp_html(otp, purpose)

    plain = f"""
Hello,

Thank you for using AP Tourism.

Your verification code is: {otp}

This code will expire in 5 minutes.

If you did not request this email, please ignore it.

AP Tourism Team
"""

    return await send_email(
        to=to,
        subject=subject,
        html_body=html,
        plain_body=plain,
    )


# ─────────────────────────────────────────────
# BOOKING CONFIRMATION EMAIL
# ─────────────────────────────────────────────

async def send_booking_confirmation(
    to: str,
    booking_number: str,
    amount: float,
) -> bool:

    subject = f"Your AP Tourism booking is confirmed — {booking_number}"

    html = f"""
    <div style="font-family:Arial;max-width:520px;margin:auto;padding:20px;">
        <h2 style="color:#1a56db;">Booking Confirmed ✓</h2>

        <p>Hello,</p>

        <p>Your booking <b>{booking_number}</b> has been confirmed.</p>

        <p>Total Amount: <b>₹{amount:.2f}</b></p>

        <p>Thank you for choosing <b>AP Tourism</b>.</p>
    </div>
    """

    plain = f"""
Hello,

Your booking {booking_number} has been confirmed.

Total amount: ₹{amount:.2f}

Thank you for choosing AP Tourism.
"""

    return await send_email(
        to=to,
        subject=subject,
        html_body=html,
        plain_body=plain,
    )