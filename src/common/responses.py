

import math
from typing import Any, Optional, Generic, TypeVar, List
from pydantic import BaseModel
from typing import Any, Optional
from pydantic import BaseModel


T = TypeVar("T")


class ResponseSchema(BaseModel):
    success: bool = True
    data: Any = None
    message: str = ""

    @classmethod
    def ok(cls, data: Any = None, message: str = "Success"):
        # convert pydantic objects or lists to dict
        if isinstance(data, list):
            serialized = []
            for item in data:
                if hasattr(item, 'model_dump'):
                    serialized.append(item.model_dump())
                else:
                    serialized.append(item)
            data = serialized
        elif hasattr(data, 'model_dump'):
            data = data.model_dump()
        return cls(success=True, data=data, message=message)

    @classmethod
    def fail(cls, message: str = "Something went wrong"):
        return cls(success=False, data=None, message=message)


class PaginatedResponse(BaseModel):
    success: bool = True
    data: Any = []
    total: int = 0
    page: int = 1
    pages: int = 1
    message: str = ""

    @classmethod
    def ok(cls, data: List[Any], total: int, page: int, page_size: int, message: str = "Success"):
        pages = math.ceil(total / page_size) if page_size > 0 and total > 0 else 1
        serialized = []
        for item in data:
            if hasattr(item, 'model_dump'):
                serialized.append(item.model_dump())
            else:
                serialized.append(item)
        return cls(
            success=True,
            data=serialized,
            total=total,
            page=page,
            pages=pages,
            message=message
        )
    
    # APIResponse — alias for LEV146 compatibility

class APIResponse(BaseModel):
    status:  str
    message: str
    data:    Optional[Any] = None

    @classmethod
    def success(cls, message: str = "Success", data: Any = None):
        return cls(status="success", message=message, data=data)

    @classmethod
    def error(cls, message: str = "Error", data: Any = None):
        return cls(status="error", message=message, data=data)