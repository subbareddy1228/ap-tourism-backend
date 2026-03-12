"""
common/responses.py
Standard API response format used across all endpoints.
"""

from typing import Any, Optional
from pydantic import BaseModel
from src.common.enums import UserRole, UserStatus, OTPPurpose



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

