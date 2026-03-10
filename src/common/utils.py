import random
import string
import uuid
from datetime import datetime, date
from typing import Optional


def generate_booking_reference(prefix: str = "APT") -> str:
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"{prefix}-{suffix}"


def generate_uuid() -> uuid.UUID:
    return uuid.uuid4()


def today() -> date:
    return datetime.utcnow().date()


def format_time(t) -> Optional[str]:
    if t is None:
        return None
    return t.strftime("%H:%M")