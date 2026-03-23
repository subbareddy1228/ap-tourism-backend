"""
integrations/ttd_api.py

TTD (Tirumala Tirupati Devasthanams) API integration.

TTD does not have an official public API. This module implements
the integration using their unofficial booking portal endpoints.
Set TTD_BASE_URL and TTD_API_KEY in .env once you have credentials.

Until real credentials are available, all methods fall back to
mock responses so darshan booking flows don't crash in development.
"""

import logging
from datetime import date
from typing import Optional

import httpx

from src.core.config import settings

logger = logging.getLogger(__name__)

TTD_BASE_URL = getattr(settings, "TTD_BASE_URL", "")
TTD_API_KEY  = getattr(settings, "TTD_API_KEY",  "")
TTD_TIMEOUT  = 10.0

_MOCK_MODE = not TTD_BASE_URL or not TTD_API_KEY


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {TTD_API_KEY}",
        "Content-Type":  "application/json",
        "Accept":        "application/json",
    }


# ─────────────────────────────────────────────
# SLOT AVAILABILITY
# ─────────────────────────────────────────────

async def get_darshan_slots(temple_id: str, darshan_date: date) -> list[dict]:
    """
    Fetch available darshan slots for a temple on a given date.

    Returns list of slot dicts:
      { slot_id, slot_time, darshan_type, quota, booked_count, available_count }
    """
    if _MOCK_MODE:
        logger.warning("TTD_API mock mode — returning dummy slots for temple_id=%s", temple_id)
        return [
            {
                "slot_id":         "SLOT001",
                "slot_time":       "06:00",
                "darshan_type":    "FREE",
                "quota":           1000,
                "booked_count":    240,
                "available_count": 760,
            },
            {
                "slot_id":         "SLOT002",
                "slot_time":       "09:00",
                "darshan_type":    "SPECIAL_ENTRY",
                "quota":           300,
                "booked_count":    120,
                "available_count": 180,
            },
        ]

    url = f"{TTD_BASE_URL}/temples/{temple_id}/darshan-slots"
    params = {"date": darshan_date.isoformat()}

    async with httpx.AsyncClient(timeout=TTD_TIMEOUT) as client:
        resp = client.get(url, headers=_headers(), params=params)
        resp.raise_for_status()
        return resp.json().get("slots", [])


# ─────────────────────────────────────────────
# SLOT AVAILABILITY CHECK
# ─────────────────────────────────────────────

async def check_slot_availability(slot_id: str, devotee_count: int) -> dict:
    """
    Check if a specific slot has quota for the requested number of devotees.

    Returns: { available: bool, available_count: int, message: str }
    """
    if _MOCK_MODE:
        return {"available": True, "available_count": 500, "message": "Slots available (mock)."}

    url = f"{TTD_BASE_URL}/slots/{slot_id}/availability"
    params = {"count": devotee_count}

    async with httpx.AsyncClient(timeout=TTD_TIMEOUT) as client:
        resp = client.get(url, headers=_headers(), params=params)
        resp.raise_for_status()
        return resp.json()


# ─────────────────────────────────────────────
# BOOKING
# ─────────────────────────────────────────────

async def create_darshan_booking(
    slot_id:    str,
    devotees:   list[dict],   # [{ name, age, id_proof_type, id_proof_number }]
    contact:    dict,         # { name, phone, email }
    booking_ref: str,         # your internal booking ID
) -> dict:
    """
    Submit a darshan booking to TTD.

    Returns: { ttd_booking_id, status, confirmation_code, message }
    """
    if _MOCK_MODE:
        import uuid
        mock_id = f"TTD-MOCK-{uuid.uuid4().hex[:8].upper()}"
        logger.warning("TTD_API mock mode — returning dummy booking id=%s", mock_id)
        return {
            "ttd_booking_id":    mock_id,
            "status":            "CONFIRMED",
            "confirmation_code": mock_id,
            "message":           "Booking confirmed (mock mode — configure TTD_BASE_URL and TTD_API_KEY for live).",
        }

    url = f"{TTD_BASE_URL}/bookings"
    payload = {
        "slot_id":    slot_id,
        "devotees":   devotees,
        "contact":    contact,
        "booking_ref": booking_ref,
    }

    async with httpx.AsyncClient(timeout=TTD_TIMEOUT) as client:
        resp = client.post(url, headers=_headers(), json=payload)
        resp.raise_for_status()
        return resp.json()


# ─────────────────────────────────────────────
# BOOKING STATUS
# ─────────────────────────────────────────────

async def get_booking_status(ttd_booking_id: str) -> dict:
    """
    Fetch current status of a TTD booking.

    Returns: { ttd_booking_id, status, confirmation_code }
    """
    if _MOCK_MODE:
        return {"ttd_booking_id": ttd_booking_id, "status": "CONFIRMED", "confirmation_code": ttd_booking_id}

    url = f"{TTD_BASE_URL}/bookings/{ttd_booking_id}"

    async with httpx.AsyncClient(timeout=TTD_TIMEOUT) as client:
        resp = client.get(url, headers=_headers())
        resp.raise_for_status()
        return resp.json()


# ─────────────────────────────────────────────
# CANCELLATION
# ─────────────────────────────────────────────

async def cancel_booking(ttd_booking_id: str, reason: Optional[str] = None) -> dict:
    """
    Cancel a TTD darshan booking.

    Returns: { success: bool, message: str }
    """
    if _MOCK_MODE:
        return {"success": True, "message": "Booking cancelled (mock)."}

    url = f"{TTD_BASE_URL}/bookings/{ttd_booking_id}/cancel"
    payload = {"reason": reason or "Customer request"}

    async with httpx.AsyncClient(timeout=TTD_TIMEOUT) as client:
        resp = client.post(url, headers=_headers(), json=payload)
        resp.raise_for_status()
        return resp.json()
