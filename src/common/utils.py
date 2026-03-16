import random
import string
from datetime import date


def generate_reference(prefix: str) -> str:
    """
    Generate a unique booking reference.
    Format: PREFIX-YYYYMMDD-XXXX
    Example: DRS-20260315-A3KP
    Used by: DarshanBooking, PoojaBooking, PrasadamOrder
    """
    today  = date.today().strftime("%Y%m%d")
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{prefix}-{today}-{suffix}"


def mask_sensitive(value: str, visible_chars: int = 4) -> str:
    """
    Mask sensitive strings for logging.
    Example: mask_sensitive("4111111111111111") → "************1111"
    SOW: Never log card numbers, JWT tokens, passwords.
    """
    if not value or len(value) <= visible_chars:
        return "*" * len(value) if value else ""
    return "*" * (len(value) - visible_chars) + value[-visible_chars:]


def rupees(amount: float) -> str:
    """Format a float as Indian Rupees string. Example: 1500.0 → '₹1,500.00'"""
    return f"₹{amount:,.2f}"