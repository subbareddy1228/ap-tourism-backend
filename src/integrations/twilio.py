"""
integrations/twilio.py
Twilio SMS integration for sending OTPs.
Supports both Twilio and MSG91 based on SMS_PROVIDER setting in .env
"""

import httpx
from twilio.rest import Client as TwilioClient
from src.core.config import settings


# ═══════════════════════════════════════════════════════════════
# TWILIO
# ═══════════════════════════════════════════════════════════════

async def send_otp_twilio(phone: str, otp: str) -> bool:
    """
    Send OTP via Twilio SMS.

    Requirements in .env:
        TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
        TWILIO_AUTH_TOKEN=your_auth_token
        TWILIO_FROM_NUMBER=+1234567890

    Args:
        phone: 10-digit Indian number e.g. "9876543210"
        otp:   6-digit OTP string e.g. "482910"

    Returns:
        True if sent successfully, raises Exception on failure.
    """
    # Format to E.164 format (+91 for India)
    to_number = f"+91{phone}"

    message_body = (
        f"Your AP Tourism OTP is: {otp}\n"
        f"Valid for 5 minutes. Do not share with anyone."
    )

    try:
        client = TwilioClient(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN
        )
        message = client.messages.create(
            body=message_body,
            from_=settings.TWILIO_FROM_NUMBER,
            to=to_number
        )
        print(f"✅ Twilio SMS sent → SID: {message.sid}")
        return True

    except Exception as e:
        print(f"❌ Twilio SMS failed: {e}")
        raise RuntimeError(f"Failed to send SMS via Twilio: {str(e)}")


# ═══════════════════════════════════════════════════════════════
# MSG91 (Alternative — popular in India)
# ═══════════════════════════════════════════════════════════════

async def send_otp_msg91(phone: str, otp: str) -> bool:
    """
    Send OTP via MSG91 (recommended for India — cheaper, faster).

    Requirements in .env:
        MSG91_API_KEY=your_api_key
        MSG91_TEMPLATE_ID=your_template_id

    Args:
        phone: 10-digit Indian number e.g. "9876543210"
        otp:   6-digit OTP string e.g. "482910"

    Returns:
        True if sent successfully, raises Exception on failure.
    """
    url = "https://control.msg91.com/api/v5/otp"

    payload = {
        "template_id": settings.MSG91_TEMPLATE_ID,
        "mobile":      f"91{phone}",   # MSG91 format: country_code + number
        "authkey":     settings.MSG91_API_KEY,
        "otp":         otp,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10.0)
            response.raise_for_status()
            data = response.json()

            if data.get("type") == "success":
                print(f"✅ MSG91 OTP sent to {phone}")
                return True
            else:
                raise RuntimeError(f"MSG91 error: {data.get('message', 'Unknown error')}")

    except httpx.HTTPError as e:
        print(f"❌ MSG91 HTTP error: {e}")
        raise RuntimeError(f"Failed to send SMS via MSG91: {str(e)}")


# ═══════════════════════════════════════════════════════════════
# UNIFIED SENDER — auto-picks provider from .env
# ═══════════════════════════════════════════════════════════════

async def send_sms(phone: str, otp: str) -> bool:
    """
    Main SMS sender — automatically picks Twilio or MSG91
    based on SMS_PROVIDER setting in your .env file.

    Usage in auth_service.py:
        from src.integrations.twilio import send_sms
        await send_sms(phone, otp)

    .env setting:
        SMS_PROVIDER=twilio   → uses Twilio
        SMS_PROVIDER=msg91    → uses MSG91
    """
    if settings.DEBUG:
        # In development — just print OTP, don't actually send SMS
        print(f"\n{'='*40}")
        print(f"  📱 DEV MODE — OTP for {phone}: {otp}")
        print(f"{'='*40}\n")
        return True

    if settings.SMS_PROVIDER == "twilio":
        return await send_otp_twilio(phone, otp)
    elif settings.SMS_PROVIDER == "msg91":
        return await send_otp_msg91(phone, otp)
    else:
        raise ValueError(
            f"Unknown SMS_PROVIDER: '{settings.SMS_PROVIDER}'. "
            "Use 'twilio' or 'msg91' in your .env"
        )
