from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Request params ────────────────────────────────────────────────────────────

class TempleSearchParams(BaseModel):
    q:            Optional[str] = None
    name:         Optional[str] = None
    deity:        Optional[str] = None
    district:     Optional[str] = None
    darshan_type: Optional[str] = None
    page: int = Field(default=1,  ge=1)
    size: int = Field(default=10, ge=1, le=50)


class HotelSearchParams(BaseModel):
    q:           Optional[str]        = None
    name:        Optional[str]        = None
    city:        Optional[str]        = None
    amenities:   Optional[list[str]]  = None
    min_price:   Optional[float]      = None
    max_price:   Optional[float]      = None
    star_rating: Optional[int]        = Field(default=None, ge=1, le=5)
    page: int = Field(default=1,  ge=1)
    size: int = Field(default=10, ge=1, le=50)


class PackageSearchParams(BaseModel):
    q:            Optional[str]   = None
    name:         Optional[str]   = None
    destination:  Optional[str]   = None
    min_duration: Optional[int]   = None
    max_duration: Optional[int]   = None
    min_budget:   Optional[float] = None
    max_budget:   Optional[float] = None
    package_type: Optional[str]   = None
    page: int = Field(default=1,  ge=1)
    size: int = Field(default=10, ge=1, le=50)


class DestinationSearchParams(BaseModel):
    q:                Optional[str] = None
    name:             Optional[str] = None
    destination_type: Optional[str] = None
    district:         Optional[str] = None
    page: int = Field(default=1,  ge=1)
    size: int = Field(default=10, ge=1, le=50)


# ── Response models ───────────────────────────────────────────────────────────

class SearchHit(BaseModel):
    id:    str
    type:  str
    name:  str
    score: float
    data:  dict[str, Any]


class GlobalSearchResult(BaseModel):
    query:        str
    total:        int
    temples:      list[SearchHit]
    hotels:       list[SearchHit]
    packages:     list[SearchHit]
    destinations: list[SearchHit]


class SuggestionItem(BaseModel):
    text: str
    type: str
    id:   str


class AutocompleteItem(BaseModel):
    name: str
    type: str
    id:   str


class EntitySearchResult(BaseModel):
    query:   Optional[str]
    total:   int
    page:    int
    size:    int
    results: list[SearchHit]
    facets:  Optional[dict[str, Any]] = None
