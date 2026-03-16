import math
from typing import TypeVar, Generic, List, Any
from pydantic import BaseModel

T = TypeVar("T")


# ─────────────────────────────────────────────
# Pagination Params
# SOW: List endpoints use GET /?page=1&limit=20
# ─────────────────────────────────────────────
class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 20

    @property
    def skip(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


# ─────────────────────────────────────────────
# Paginated Response
# SOW: Response includes data, total, page, pages
# ─────────────────────────────────────────────
class PaginatedResponse(BaseModel, Generic[T]):
    success: bool = True
    data: List[Any] = []
    total: int = 0
    page: int = 1
    pages: int = 1
    message: str = ""

    @classmethod
    def ok(
        cls,
        data: List[Any],
        total: int,
        page: int,
        page_size: int,
        message: str = "Success"
    ):
        pages = math.ceil(total / page_size) if page_size > 0 and total > 0 else 1
        return cls(
            success=True,
            data=data,
            total=total,
            page=page,
            pages=pages,
            message=message
        )


def paginate(query, page: int, page_size: int):
    """
    Helper to paginate a SQLAlchemy query.
    Returns (items, total)
    """
    total = query.count()
    skip = (page - 1) * page_size
    items = query.offset(skip).limit(page_size).all()
    return items, total