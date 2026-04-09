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
        )"""
integrations/twilio.py
Async SMS integration — supports MSG91 (default) and Twilio.

Provider is selected by SMS_PROVIDER in your .env file:
    SMS_PROVIDER=msg91    ← use this (recommended for India)
    SMS_PROVIDER=twilio   ← use this only if you have Twilio

─────────────────────────────────────────────────────────────
HOW TO SETUP MSG91 (step by step)
─────────────────────────────────────────────────────────────
1. Go to https://msg91.com → Sign up / Login
2. Dashboard → API → Copy your Auth Key
3. Dashboard → SMS → Templates → Create OTP Template
   - Template must contain ##OTP## placeholder
   - Example: "Your AP Tourism OTP is ##OTP##. Valid for 5 min."
   - After approval copy the Template ID
4. Add to your .env:
       SMS_PROVIDER=msg91
       MSG91_API_KEY=your_auth_key_here
       MSG91_TEMPLATE_ID=your_template_id_here
5. Set DEBUG=False in .env (DEBUG=True skips actual SMS)

─────────────────────────────────────────────────────────────
HOW TO SETUP TWILIO (if you prefer Twilio)
─────────────────────────────────────────────────────────────
1. Go to https://console.twilio.com
2. Get Account SID, Auth Token, and a From Number
3. Add to your .env:
       SMS_PROVIDER=twilio
       TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
       TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
       TWILIO_FROM_NUMBER=+1xxxxxxxxxx
4. Set DEBUG=False in .env
"""

import base64
import logging
import httpx

from src.core.config import settings

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# MSG91  (recommended for India)
# ═══════════════════════════════════════════════════════════════

async def send_otp_msg91(phone: str, otp: str) -> bool:
    """
    Send OTP via MSG91 OTP API v5.

    Required .env:
        MSG91_API_KEY      — your MSG91 Auth Key
        MSG91_TEMPLATE_ID  — approved OTP template ID

    The template MUST contain ##OTP## placeholder, e.g.:
        "Your AP Tourism OTP is ##OTP##. Valid for 5 minutes. Do not share."

    Args:
        phone: 10-digit Indian mobile number (no country code, no +91)
        otp:   6-digit OTP string

    Returns:
        True on success

    Raises:
        RuntimeError on failure
    """
    if not settings.MSG91_API_KEY or not settings.MSG91_TEMPLATE_ID:
        raise RuntimeError(
            "MSG91 is not configured. "
            "Add MSG91_API_KEY and MSG91_TEMPLATE_ID to your .env file. "
            "See https://msg91.com → Dashboard → API for your Auth Key."
        )

    url = "https://control.msg91.com/api/v5/otp"

    payload = {
        "template_id": settings.MSG91_TEMPLATE_ID,
        "mobile":      f"91{phone}",          # MSG91 needs country code prefix
        "authkey":     settings.MSG91_API_KEY,
        "otp":         otp,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()

            data = response.json()

            if data.get("type") == "success":
                logger.info("✅ MSG91 OTP sent  phone=%s", phone)
                return True
            else:
                error_msg = data.get("message", "Unknown MSG91 error")
                logger.error("MSG91 error  phone=%s  response=%s", phone, data)
                raise RuntimeError(f"MSG91 error: {error_msg}")

    except httpx.HTTPStatusError as e:
        logger.error("MSG91 HTTP error  phone=%s  status=%s  body=%s",
                     phone, e.response.status_code, e.response.text)
        raise RuntimeError(f"MSG91 HTTP {e.response.status_code}: {e.response.text}")

    except httpx.HTTPError as e:
        logger.error("MSG91 connection error  phone=%s  error=%s", phone, str(e))
        raise RuntimeError(f"MSG91 connection failed: {str(e)}")


# ═══════════════════════════════════════════════════════════════
# TWILIO
# ═══════════════════════════════════════════════════════════════

async def send_otp_twilio(phone: str, otp: str) -> bool:
    """
    Send OTP via Twilio REST API (async, no Twilio SDK needed).

    Required .env:
        TWILIO_ACCOUNT_SID  — starts with AC
        TWILIO_AUTH_TOKEN
        TWILIO_FROM_NUMBER  — your Twilio phone number e.g. +1xxxxxxxxxx

    Args:
        phone: 10-digit Indian mobile number (no country code)
        otp:   6-digit OTP string
    """
    if (not settings.TWILIO_ACCOUNT_SID
            or not settings.TWILIO_AUTH_TOKEN
            or not settings.TWILIO_FROM_NUMBER):
        raise RuntimeError(
            "Twilio is not configured. "
            "Add TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER to your .env file."
        )

    to_number   = f"+91{phone}"
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
                    "To":   to_number,
                    "Body": message_body,
                },
                headers={
                    "Authorization": f"Basic {credentials}",
                    "Content-Type":  "application/x-www-form-urlencoded",
                },
            )
            response.raise_for_status()
            logger.info("✅ Twilio OTP sent  phone=%s", phone)
            return True

    except httpx.HTTPStatusError as e:
        logger.error("Twilio HTTP error  phone=%s  status=%s  body=%s",
                     phone, e.response.status_code, e.response.text)
        raise RuntimeError(f"Twilio HTTP {e.response.status_code}: {e.response.text}")

    except httpx.HTTPError as e:
        logger.error("Twilio connection error  phone=%s  error=%s", phone, str(e))
        raise RuntimeError(f"Twilio SMS failed: {str(e)}")


# ═══════════════════════════════════════════════════════════════
# UNIFIED SENDER  ← this is what all services call
# ═══════════════════════════════════════════════════════════════

async def send_sms(phone: str, otp: str) -> bool:
    """
    Unified SMS sender — called by auth_service, user_service, notification_service.

    Reads SMS_PROVIDER from .env:
        SMS_PROVIDER=msg91    → uses MSG91
        SMS_PROVIDER=twilio   → uses Twilio

    In DEBUG mode (DEBUG=True in .env):
        Skips actual SMS and prints OTP to terminal.
        Use this during local development.

    Args:
        phone: 10-digit Indian mobile number
        otp:   6-digit OTP string (or any message text)
    """
    # ── Development mode: print to terminal, skip SMS ─────────
    if settings.DEBUG:
        logger.info("🔧 DEV MODE — skipping SMS  phone=%s  otp=%s", phone, otp)
        print("\n" + "=" * 45)
        print(f"  📱 DEV OTP  |  Phone: {phone}  |  OTP: {otp}")
        print("=" * 45 + "\n")
        return True

    # ── Production: route to configured provider ──────────────
    provider = (settings.SMS_PROVIDER or "msg91").lower().strip()

    if provider == "msg91":
        return await send_otp_msg91(phone, otp)

    elif provider == "twilio":
        return await send_otp_twilio(phone, otp)

    else:
        raise ValueError(
            f"Unknown SMS_PROVIDER='{provider}' in .env. "
            f"Valid values: 'msg91' or 'twilio'."
        )