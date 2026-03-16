# from typing import Any, Optional
# from fastapi.responses import JSONResponse


# def success_response(
#     data: Any = None,
#     message: str = "Success",
#     status_code: int = 200,
# ) -> JSONResponse:
#     return JSONResponse(
#         status_code=status_code,
#         content={
#             "success": True,
#             "message": message,
#             "data": data,
#         },
#     )


# def error_response(
#     message: str = "An error occurred",
#     status_code: int = 400,
#     details: Optional[Any] = None,
# ) -> JSONResponse:
#     return JSONResponse(
#         status_code=status_code,
#         content={
#             "success": False,
#             "message": message,
#             "details": details,
#         },
#     )

import math
from typing import Any, Optional, Generic, TypeVar, List
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