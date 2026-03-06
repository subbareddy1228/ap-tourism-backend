"""
common/responses.py
Standard API response format used across all endpoints.
"""

from typing import Any, Optional
from pydantic import BaseModel


class APIResponse(BaseModel):
    status: str
    message: str
    data: Optional[Any] = None

    @classmethod
    def success(cls, message: str = "Success", data: Any = None):
        return cls(status="success", message=message, data=data)

    @classmethod
    def error(cls, message: str = "Error", data: Any = None):
        return cls(status="error", message=message, data=data)


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
