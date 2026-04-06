"""
common/enums.py
Centralised enum definitions for the entire AP Tourism backend.

Rules (never violate):
  - All enums inherit (str, Enum) so they serialise cleanly to JSON strings.
  - Values are lowercase strings for BookingType / statuses so they match
    the PostgreSQL Enum type values created in the initial migration.
  - Never duplicate enum definitions in model files — always import from here.

Changes vs original:
  BookingType — added POOJA, PRASADAM, GUIDE, COMBO, CUSTOM.
                These 5 values are referenced by booking_service.py,
                booking_repo.py, and schemas/booking.py but were missing,
                causing AttributeError on every corresponding endpoint.
"""

from enum import Enum


# ── User ──────────────────────────────────────────────────────────────────────

class UserRole(str, Enum):
    TRAVELER = "traveler"
    PARTNER  = "partner"
    GUIDE    = "guide"
    ADMIN    = "admin"
    DRIVER   = "driver"


class UserStatus(str, Enum):
    ACTIVE    = "active"
    INACTIVE  = "inactive"
    SUSPENDED = "suspended"
    DELETED   = "deleted"


class OTPPurpose(str, Enum):
    REGISTER        = "register"
    LOGIN           = "login"
    FORGOT_PASSWORD = "forgot_password"
    VERIFY_PHONE    = "verify_phone"
    VERIFY_EMAIL    = "verify_email"


# ── Booking ───────────────────────────────────────────────────────────────────

class BookingType(str, Enum):
    HOTEL    = "hotel"
    VEHICLE  = "vehicle"
    DARSHAN  = "darshan"
    PACKAGE  = "package"
    # ── Added (were missing — crashed 5 endpoints) ──
    POOJA    = "pooja"
    PRASADAM = "prasadam"
    GUIDE    = "guide"
    COMBO    = "combo"
    CUSTOM   = "custom"


class BookingStatus(str, Enum):
    PENDING   = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class PaymentStatus(str, Enum):
    PENDING  = "pending"
    SUCCESS  = "success"
    FAILED   = "failed"
    REFUNDED = "refunded"


class DeliveryStatus(str, Enum):
    PENDING   = "pending"
    SHIPPED   = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


# ── Vehicle / Trip ────────────────────────────────────────────────────────────

class TripType(str, Enum):
    ONE_WAY    = "one_way"
    ROUND_TRIP = "round_trip"


# ── People ────────────────────────────────────────────────────────────────────

class Gender(str, Enum):
    MALE   = "male"
    FEMALE = "female"
    OTHER  = "other"


# ── Package ───────────────────────────────────────────────────────────────────

class PackageType(str, Enum):
    PILGRIMAGE = "PILGRIMAGE"
    LEISURE    = "LEISURE"
    ADVENTURE  = "ADVENTURE"


# ── Localisation ─────────────────────────────────────────────────────────────

class LanguageEnum(str, Enum):
    EN = "en"
    HI = "hi"
    TE = "te"