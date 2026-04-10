"""
integrations/msg91.py
Async SMS integration — MSG91 (default) and Twilio.

Set SMS_PROVIDER in .env:
    SMS_PROVIDER=msg91    <- recommended for India
    SMS_PROVIDER=twilio   <- if you have Twilio
    DEBUG=True            <- prints OTP to terminal, skips real SMS (for development)
"""

import base64
import logging
import httpx

from src.core.config import settings

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# MSG91
# ═══════════════════════════════════════════════════════════════

async def send_otp_msg91(phone: str, otp: str) -> bool:
    if not settings.MSG91_API_KEY or not settings.MSG91_TEMPLATE_ID:
        raise RuntimeError(
            "MSG91 not configured. "
            "Add MSG91_API_KEY and MSG91_TEMPLATE_ID to your .env file."
        )

    url = "https://control.msg91.com/api/v5/otp"

    payload = {
        "template_id": settings.MSG91_TEMPLATE_ID,
        "mobile":      f"91{phone}",
        "authkey":     settings.MSG91_API_KEY,
        "otp":         otp,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            if data.get("type") == "success":
                logger.info("MSG91 OTP sent  phone=%s", phone)
                return True

            error_msg = data.get("message", "Unknown error")
            logger.error("MSG91 error  phone=%s  response=%s", phone, data)
            raise RuntimeError(f"MSG91 error: {error_msg}")

    except httpx.HTTPStatusError as e:
        logger.error("MSG91 HTTP error  phone=%s  status=%s", phone, e.response.status_code)
        raise RuntimeError(f"MSG91 HTTP {e.response.status_code}: {e.response.text}")

    except httpx.HTTPError as e:
        logger.error("MSG91 connection error  phone=%s  error=%s", phone, str(e))
        raise RuntimeError(f"MSG91 connection failed: {str(e)}")


# ═══════════════════════════════════════════════════════════════
# TWILIO
# ═══════════════════════════════════════════════════════════════

async def send_otp_twilio(phone: str, otp: str) -> bool:
    if (
        not settings.TWILIO_ACCOUNT_SID
        or not settings.TWILIO_AUTH_TOKEN
        or not settings.TWILIO_FROM_NUMBER
    ):
        raise RuntimeError(
            "Twilio not configured. "
            "Add TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER to .env."
        )

    to_number = f"+91{phone}"
    message_body = (
        f"Your AP Tourism OTP is: {otp}. "
        f"Valid for 5 minutes. Do not share."
    )
    url = (
        "https://api.twilio.com/2010-04-01/Accounts/"
        + settings.TWILIO_ACCOUNT_SID
        + "/Messages.json"
    )
    credentials = base64.b64encode(
        f"{settings.TWILIO_ACCOUNT_SID}:{settings.TWILIO_AUTH_TOKEN}".encode()
    ).decode()

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                data={
                    "From": settings.TWILIO_FROM_NUMBER,
                    "To":   to_number,
                    "Body": message_body,
                },
                headers={
                    "Authorization": f"Basic {credentials}",
                    "Content-Type":  "application/x-www-form-urlencoded",
                },
            )
            response.raise_for_status()
            logger.info("Twilio OTP sent  phone=%s", phone)
            return True

    except httpx.HTTPStatusError as e:
        logger.error("Twilio HTTP error  phone=%s  status=%s", phone, e.response.status_code)
        raise RuntimeError(f"Twilio HTTP {e.response.status_code}: {e.response.text}")

    except httpx.HTTPError as e:
        logger.error("Twilio connection error  phone=%s  error=%s", phone, str(e))
        raise RuntimeError(f"Twilio SMS failed: {str(e)}")


# ═══════════════════════════════════════════════════════════════
# UNIFIED SENDER
# ═══════════════════════════════════════════════════════════════

async def send_sms(phone: str, otp: str) -> bool:
    """
    Called by auth_service, user_service, notification_service.
    Routes to MSG91 or Twilio based on SMS_PROVIDER in .env.
    In DEBUG=True mode, prints OTP to terminal and skips real SMS.
    """
    if settings.DEBUG:
        logger.info("DEV MODE — skipping SMS  phone=%s  otp=%s", phone, otp)
        print("\n" + "=" * 45)
        print(f"  DEV OTP  |  Phone: {phone}  |  OTP: {otp}")
        print("=" * 45 + "\n")
        return True

    provider = (settings.SMS_PROVIDER or "msg91").lower().strip()

    if provider == "msg91":
        return await send_otp_msg91(phone, otp)
    elif provider == "twilio":
        return await send_otp_twilio(phone, otp)
    else:
        raise ValueError(
            f"Unknown SMS_PROVIDER='{provider}'. Valid values: 'msg91' or 'twilio'."
        )