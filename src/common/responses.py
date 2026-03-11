
from typing import Any, Optional
from pydantic import BaseModel

class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None

    @classmethod
    def ok(cls, message: str, data: Any = None) -> "APIResponse":
        return cls(success=True, message=message, data=data)

    @classmethod
    def fail(cls, message: str, data: Any = None) -> "APIResponse":
        return cls(success=False, message=message, data=data)