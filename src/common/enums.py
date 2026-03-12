
"""
common/enums.py
All enums used in the project.
"""

from enum import Enum


class UserRole(str, Enum):
    TRAVELER = "traveler"
    PARTNER  = "partner"
    GUIDE    = "guide"
    ADMIN    = "admin"


class OTPPurpose(str, Enum):
    REGISTER       = "register"
    LOGIN          = "login"
    FORGOT_PASSWORD = "forgot_password"
    VERIFY_PHONE   = "verify_phone"
    VERIFY_EMAIL   = "verify_email"


class UserStatus(str, Enum):
    ACTIVE    = "active"
    INACTIVE  = "inactive"
    SUSPENDED = "suspended"
    DELETED   = "deleted"
