"""
integrations/msg91.py
SMS integration — MSG91 (default for India) + Twilio fallback.

.env settings:
    SMS_PROVIDER=msg91
    MSG91_API_KEY=your_authkey
    MSG91_TEMPLATE_ID=your_template_id
    MSG91_SENDER_ID=APTRMS
    DEBUG=False
"""

import base64
import logging
import httpx

from src.core.config import settings

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# MSG91 — authkey in HEADER (correct per MSG91 v5 docs)
# ═══════════════════════════════════════════════════════════════

async def send_otp_msg91(phone: str, otp: str) -> bool:
    """Send OTP via MSG91 API v5 — authkey passed in header."""

    if not settings.MSG91_API_KEY or not settings.MSG91_TEMPLATE_ID:
        raise RuntimeError(
            "MSG91 not configured. "
            "Set MSG91_API_KEY and MSG91_TEMPLATE_ID in .env"
        )

    # Normalize phone → 919381772845
    phone = phone.strip().replace(" ", "").replace("-", "")
    if phone.startswith("+91"):
        phone = phone[3:]
    if phone.startswith("91") and len(phone) == 12:
        mobile = phone
    else:
        mobile = f"91{phone}"

    url = "https://api.msg91.com/api/v5/otp"

    # ── authkey MUST go in header per MSG91 v5 docs ───────────
    headers = {
        "authkey":      settings.MSG91_API_KEY,
        "Content-Type": "application/json",
        "Accept":       "application/json",
    }

    payload = {
        "template_id": settings.MSG91_TEMPLATE_ID,
        "mobile":      mobile,
        "otp":         str(otp),
        "otp_expiry":  5,
        "sender":      getattr(settings, "MSG91_SENDER_ID", "APTRMS"),
    }

    logger.info("MSG91 sending to mobile=%s template=%s sender=%s",
                mobile, settings.MSG91_TEMPLATE_ID, payload["sender"])

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json=payload, headers=headers)

        logger.info("MSG91 status=%d body=%s", response.status_code, response.text)

        data = response.json()

        if data.get("type") == "success":
            logger.info("MSG91 OTP sent successfully mobile=%s request_id=%s",
                        mobile, data.get("request_id", ""))
            return True

        error = data.get("message") or data.get("error") or str(data)
        logger.error("MSG91 failed mobile=%s error=%s full_response=%s",
                     mobile, error, data)
        raise RuntimeError(f"MSG91 error: {error}")

    except httpx.HTTPStatusError as e:
        logger.error("MSG91 HTTP error status=%d body=%s",
                     e.response.status_code, e.response.text)
        raise RuntimeError(f"MSG91 HTTP {e.response.status_code}: {e.response.text}")

    except httpx.HTTPError as e:
        logger.error("MSG91 connection error=%s", str(e))
        raise RuntimeError(f"MSG91 connection failed: {str(e)}")


# ═══════════════════════════════════════════════════════════════
# TWILIO
# ═══════════════════════════════════════════════════════════════

async def send_otp_twilio(phone: str, otp: str) -> bool:
    """Send OTP via Twilio SMS API."""

    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        raise RuntimeError("Twilio not configured in .env")

    phone = phone.strip()
    if not phone.startswith("+"):
        phone = f"+91{phone}" if len(phone) == 10 else f"+{phone}"

    url = (f"https://api.twilio.com/2010-04-01/Accounts/"
           f"{settings.TWILIO_ACCOUNT_SID}/Messages.json")

    credentials = base64.b64encode(
        f"{settings.TWILIO_ACCOUNT_SID}:{settings.TWILIO_AUTH_TOKEN}".encode()
    ).decode()

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                url,
                data={
                    "From": settings.TWILIO_FROM_NUMBER,
                    "To":   phone,
                    "Body": f"Your AP Tourism OTP is: {otp}. Valid 5 mins. Do not share.",
                },
                headers={
                    "Authorization": f"Basic {credentials}",
                    "Content-Type":  "application/x-www-form-urlencoded",
                },
            )
            response.raise_for_status()
            logger.info("Twilio OTP sent phone=%s", phone)
            return True

    except httpx.HTTPStatusError as e:
        logger.error("Twilio error status=%d body=%s",
                     e.response.status_code, e.response.text)
        raise RuntimeError(f"Twilio HTTP {e.response.status_code}: {e.response.text}")

    except httpx.HTTPError as e:
        raise RuntimeError(f"Twilio failed: {str(e)}")


# ═══════════════════════════════════════════════════════════════
# UNIFIED ENTRY POINT — called by auth_service
# ═══════════════════════════════════════════════════════════════

async def send_sms(phone: str, otp: str) -> bool:
    """
    Route SMS to MSG91 or Twilio based on SMS_PROVIDER in .env.
    DEBUG=True → print OTP to terminal only.
    """

    if settings.DEBUG:
        logger.info("DEV MODE — OTP not sent via SMS  phone=%s  otp=%s", phone, otp)
        print("\n" + "=" * 45)
        print(f"  DEV OTP  |  Phone: {phone}  |  OTP: {otp}")
        print("=" * 45 + "\n")
        return True

    provider = (settings.SMS_PROVIDER or "msg91").lower().strip()
    logger.info("SMS provider=%s phone=%s", provider, phone)

    if provider == "msg91":
        return await send_otp_msg91(phone, otp)
    elif provider == "twilio":
        return await send_otp_twilio(phone, otp)
    else:
        raise ValueError(
            f"Unknown SMS_PROVIDER='{provider}'. Use 'msg91' or 'twilio'."
        )