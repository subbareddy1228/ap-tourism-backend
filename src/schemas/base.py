"""
schemas/base.py
Base Pydantic schemas reused across all modules.
"""

from typing import Any, Optional, List, Generic, TypeVar
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


DataT = TypeVar("DataT")


class APIResponse(BaseModel):
    """Standard API response envelope."""
    status:  str
    message: str
    data:    Optional[Any] = None

    @classmethod
    def success(cls, message: str = "Success", data: Any = None) -> "APIResponse":
        return cls(status="success", message=message, data=data)

    @classmethod
    def error(cls, message: str = "Error", data: Any = None) -> "APIResponse":
        return cls(status="error", message=message, data=data)


class PaginatedResponse(BaseModel, Generic[DataT]):
    """Paginated list response."""
    data:  List[DataT]
    total: int
    page:  int
    pages: int
    limit: int


class TimestampMixin(BaseModel):
    """Add created_at / updated_at to any response schema."""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UUIDMixin(BaseModel):
    """Add id field to any response schema."""
    id: UUID

    model_config = ConfigDict(from_attributes=True)


class BaseResponseSchema(UUIDMixin, TimestampMixin):
    """Full base response — id + timestamps."""
    pass


class MessageResponse(BaseModel):
    """Simple message-only response."""
    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    """Standard error response."""
    status:  str = "error"
    message: str
    detail:  Optional[Any] = None