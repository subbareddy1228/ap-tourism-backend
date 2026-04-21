"""
common/responses.py
Standard API response format used across all endpoints.

Spec format:
  Success: {success: true, data: {...}, message: ''}
  Error:   {success: false, error: '...', code: 400}
"""

from typing import Any, Optional
from pydantic import BaseModel
from fastapi.responses import JSONResponse


class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None

    @classmethod
    def success(cls, message: str = "Success", data: Any = None):
        return cls(success=True, message=message, data=data)

    @classmethod
    def error(cls, message: str = "Error", data: Any = None):
        return cls(success=False, message=message, data=data)

    @staticmethod
    def error_response(message: str = "Error", code: int = 400):
        return JSONResponse(
            status_code=code,
            content={
                "success": False,
                "error": message,
                "code": code
            }
        )