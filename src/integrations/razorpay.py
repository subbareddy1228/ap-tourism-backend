"""
integrations/razorpay.py

Real Razorpay SDK integration.
Uses razorpay==1.4.2 (already in requirements.txt).

Covers:
  - Order creation        → create_order
  - Signature verify      → verify_payment_signature  (HMAC-SHA256)
  - Webhook sig verify    → verify_webhook_signature
  - Refund creation       → create_refund
  - Refund status fetch   → get_refund_status
"""

import asyncio
import hashlib
import hmac
import logging

import razorpay

from src.core.config import settings

logger = logging.getLogger(__name__)


def _client() -> razorpay.Client:
    """Return an authenticated Razorpay client."""
    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )


# ─────────────────────────────────────────────
# ORDER CREATION
# ─────────────────────────────────────────────

async def create_order(amount_inr: float, booking_id: str, notes: dict = None) -> dict:
    """
    Create a Razorpay order.
    Runs the blocking SDK call in a thread pool to avoid blocking the event loop.
    """
    def _sync():
        amount_paise = int(round(amount_inr * 100))
        payload = {
            "amount":   amount_paise,
            "currency": "INR",
            "receipt":  str(booking_id)[:40],
            "notes":    notes or {},
        }
        order = _client().order.create(data=payload)
        logger.info(
            "Razorpay order created order_id=%s booking_id=%s amount_paise=%d",
            order["id"], booking_id, amount_paise,
        )
        return order

    try:
        return await asyncio.to_thread(_sync)
    except Exception as e:
        logger.error("Razorpay order creation failed booking_id=%s error=%s", booking_id, str(e))
        raise RuntimeError(f"Razorpay order creation failed: {str(e)}")


# ─────────────────────────────────────────────
# PAYMENT SIGNATURE VERIFICATION
# ─────────────────────────────────────────────

def verify_payment_signature(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
) -> bool:
    """
    Verify Razorpay HMAC-SHA256 payment signature.
    Pure computation — no I/O, sync is correct here.

    Formula:  HMAC_SHA256(key=KEY_SECRET, msg="order_id|payment_id")

    Returns True if valid, False otherwise.
    Never raises — logs a warning on mismatch.
    """
    body = f"{razorpay_order_id}|{razorpay_payment_id}"
    expected = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
        body.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    is_valid = hmac.compare_digest(expected, razorpay_signature)

    if not is_valid:
        logger.warning(
            "Razorpay signature mismatch order_id=%s payment_id=%s",
            razorpay_order_id, razorpay_payment_id,
        )
    return is_valid


# ─────────────────────────────────────────────
# WEBHOOK SIGNATURE VERIFICATION
# ─────────────────────────────────────────────

def verify_webhook_signature(raw_body: bytes, razorpay_signature: str) -> bool:
    """
    Verify Razorpay webhook X-Razorpay-Signature header.
    Pure computation — no I/O, sync is correct here.

    Formula:  HMAC_SHA256(key=RAZORPAY_KEY_SECRET, msg=raw_request_body)

    Call this inside POST /webhook/razorpay BEFORE processing any event.
    raw_body must be the unmodified request bytes — do NOT parse JSON first.
    """
    expected = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    is_valid = hmac.compare_digest(expected, razorpay_signature)

    if not is_valid:
        logger.warning("Razorpay webhook signature mismatch — possible spoofed request")
    return is_valid


# ─────────────────────────────────────────────
# REFUND
# ─────────────────────────────────────────────

async def create_refund(
    razorpay_payment_id: str,
    amount_inr: float,
    notes: dict = None,
) -> dict:
    """
    Initiate a partial or full refund on a captured Razorpay payment.
    Runs the blocking SDK call in a thread pool to avoid blocking the event loop.

    Args:
        razorpay_payment_id:  The pay_xxx ID from the original captured payment.
        amount_inr:           Amount to refund in INR.
        notes:                Optional metadata dict.

    Returns:
        Razorpay refund dict — keys: id, payment_id, amount, status.

    Raises:
        RuntimeError on failure.
    """
    def _sync():
        amount_paise = int(round(amount_inr * 100))
        payload = {
            "amount": amount_paise,
            "notes":  notes or {},
        }
        refund = _client().payment.refund(razorpay_payment_id, payload)
        logger.info(
            "Razorpay refund created refund_id=%s payment_id=%s amount_paise=%d",
            refund["id"], razorpay_payment_id, amount_paise,
        )
        return refund

    try:
        return await asyncio.to_thread(_sync)
    except Exception as e:
        logger.error(
            "Razorpay refund failed payment_id=%s error=%s",
            razorpay_payment_id, str(e),
        )
        raise RuntimeError(f"Razorpay refund failed: {str(e)}")


async def get_refund_status(razorpay_refund_id: str) -> dict:
    """
    Fetch current status of a Razorpay refund by refund ID.
    Runs the blocking SDK call in a thread pool to avoid blocking the event loop.

    Returns refund dict with status: pending | processed | failed.
    """
    def _sync():
        return _client().refund.fetch(razorpay_refund_id)

    try:
        return await asyncio.to_thread(_sync)
    except Exception as e:
        logger.error(
            "Razorpay fetch refund failed refund_id=%s error=%s",
            razorpay_refund_id, str(e),
        )
        raise RuntimeError(f"Failed to fetch Razorpay refund: {str(e)}")