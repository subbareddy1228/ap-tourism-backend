import re
from uuid import UUID
from typing import Optional


def is_valid_phone(phone: str) -> bool:
    """Indian mobile number: 10 digits, starts with 6-9."""
    return bool(re.match(r'^[6-9]\d{9}$', phone.strip()))


def is_valid_pincode(pincode: str) -> bool:
    """Indian pincode: exactly 6 digits."""
    return bool(re.match(r'^\d{6}$', pincode.strip()))


def is_valid_gstin(gstin: str) -> bool:
    """Basic GSTIN format validation: 15 alphanumeric characters."""
    return bool(re.match(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$', gstin.strip()))


def is_valid_pan(pan: str) -> bool:
    """PAN format: 5 letters + 4 digits + 1 letter."""
    return bool(re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', pan.strip()))


def is_valid_rating(rating: float) -> bool:
    """Rating must be between 1.0 and 5.0."""
    return 1.0 <= rating <= 5.0


def is_valid_coordinates(lat: Optional[float], lng: Optional[float]) -> bool:
    """Validate lat/lng are within valid ranges."""
    if lat is None or lng is None:
        return False
    return -90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0