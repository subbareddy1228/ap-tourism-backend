"""Standard JSON response helpers."""
from typing import Any, Optional


def success_response(data: Any = None, message: str = "Success"):
    return {"success": True, "data": data, "message": message}


def error_response(error: str, code: int = 400):
    return {"success": False, "error": error, "code": code}
