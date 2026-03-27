"""
common/responses.py
Standard API response format used across all endpoints.
"""

import code
from typing import Any, Optional
from pydantic import BaseModel
from fastapi.responses import JSONResponse





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
    

    def success_response(data=None, message="Success"):
        return {
        "success": True,
        "message": message,
        "data": data
    }

    def error_response(message="Error", code=400):
        return JSONResponse(
        status_code=code,
        content={
            "success": False,
            "error": message,
            "code": code
        }
    )

