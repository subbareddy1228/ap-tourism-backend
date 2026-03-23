"""
common/enums.py
All enums used in the project.
"""

from enum import Enum


class UserRole(str, Enum):
    TRAVELER = "traveler"
    PARTNER = "partner"
    GUIDE = "guide"
    ADMIN = "admin"


class OTPPurpose(str, Enum):
    REGISTER = "register"
    LOGIN = "login"
    FORGOT_PASSWORD = "forgot_password"
    VERIFY_PHONE = "verify_phone"
    VERIFY_EMAIL = "verify_email"


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class PackageType(str, Enum):
    PILGRIMAGE = "PILGRIMAGE"
    LEISURE = "LEISURE"
    ADVENTURE = "ADVENTURE"


class BookingType(str, Enum):
    VEHICLE = "vehicle"
    HOTEL = "hotel"
    PACKAGE = "package"
    DARSHAN = "darshan"


class BookingStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"


class TripType(str, Enum):
    ONE_WAY = "one_way"
    ROUND_TRIP = "round_trip"

class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"

class DeliveryStatus(str, Enum):
    PENDING = "pending"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"