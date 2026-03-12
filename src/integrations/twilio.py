"""
integrations/twilio.py

Async SMS integration for sending OTP messages.

Supports:
    • Twilio
    • MSG91 (recommended for India)

Provider is selected using SMS_PROVIDER in .env
"""

import base64
import logging
import httpx

from src.core.config import settings

logger = logging.getLogger(__name__)


# ============================================================
# TWILIO (ASYNC IMPLEMENTATION)
# ============================================================

async def send_otp_twilio(phone: str, otp: str) -> bool:
    """
    Send OTP via Twilio using async HTTP API.

    Required .env variables:
        TWILIO_ACCOUNT_SID
        TWILIO_AUTH_TOKEN
        TWILIO_FROM_NUMBER

    Args:
        phone: 10 digit phone number (India)
        otp: 6 digit OTP

    Returns:
        True if SMS sent successfully
    """

    to_number = f"+91{phone}"

    message_body = (
        f"Your AP Tourism OTP is: {otp}\n"
        f"Valid for 5 minutes. Do not share with anyone."
    )

    url = (
        f"https://api.twilio.com/2010-04-01/Accounts/"
        f"{settings.TWILIO_ACCOUNT_SID}/Messages.json"
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
                    "To": to_number,
                    "Body": message_body,
                },
                headers={
                    "Authorization": f"Basic {credentials}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )

            response.raise_for_status()

            logger.info("Twilio OTP sent successfully to %s", phone)

            return True

    except httpx.HTTPError as e:

        logger.error("Twilio SMS failed: %s", str(e))

        raise RuntimeError(f"Twilio SMS failed: {str(e)}")


# ============================================================
# MSG91 (INDIA SMS PROVIDER)
# ============================================================

async def send_otp_msg91(phone: str, otp: str) -> bool:
    """
    Send OTP via MSG91.

    Required .env variables:
        MSG91_API_KEY
        MSG91_TEMPLATE_ID
    """

    url = "https://control.msg91.com/api/v5/otp"

    payload = {
        "template_id": settings.MSG91_TEMPLATE_ID,
        "mobile": f"91{phone}",
        "authkey": settings.MSG91_API_KEY,
        "otp": otp,
    }

    try:

        async with httpx.AsyncClient(timeout=10.0) as client:

            response = await client.post(url, json=payload)

            response.raise_for_status()

            data = response.json()

            if data.get("type") == "success":

                logger.info("MSG91 OTP sent successfully to %s", phone)

                return True

            else:

                raise RuntimeError(
                    f"MSG91 error: {data.get('message', 'Unknown error')}"
                )

    except httpx.HTTPError as e:

        logger.error("MSG91 SMS failed: %s", str(e))

        raise RuntimeError(f"MSG91 SMS failed: {str(e)}")


# ============================================================
# UNIFIED SMS SENDER
# ============================================================

async def send_sms(phone: str, otp: str) -> bool:
    """
    Unified SMS sender.

    Automatically selects SMS provider based on .env:

        SMS_PROVIDER=twilio
        SMS_PROVIDER=msg91

    In DEBUG mode, OTP will only print in terminal.
    """

    # DEVELOPMENT MODE
    if settings.DEBUG:

        logger.info("DEV MODE OTP for %s → %s", phone, otp)

        print("\n" + "=" * 40)
        print(f"📱 DEV MODE OTP for {phone}: {otp}")
        print("=" * 40 + "\n")

        return True

    provider = settings.SMS_PROVIDER.lower()

    if provider == "twilio":

        return await send_otp_twilio(phone, otp)

    elif provider == "msg91":

        return await send_otp_msg91(phone, otp)

    else:

        raise ValueError(
            f"Invalid SMS_PROVIDER '{provider}'. Use 'twilio' or 'msg91'."
        )