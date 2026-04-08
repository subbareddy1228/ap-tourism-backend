from __future__ import annotations
from datetime import datetime, date, time
from typing import Optional, List, Any, Dict
from uuid import UUID
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────
# Temple Base
# ─────────────────────────────────────────────
class TempleBase(BaseModel):
    name:           str
    description:    Optional[str]   = None
    deity:          str
    district:       str
    address:        Optional[str]   = None
    latitude:       Optional[float] = None
    longitude:      Optional[float] = None
    dress_code:     Optional[str]   = None
    contact_number: Optional[str]   = None
    website:        Optional[str]   = None
    timings:        Optional[Dict[str, Any]] = None
    images:         Optional[List[str]]      = []


# ─────────────────────────────────────────────
# Admin — Create Temple
# POST /
# ─────────────────────────────────────────────
class TempleCreate(TempleBase):
    is_featured: Optional[bool] = False
    is_active:   Optional[bool] = True


# ─────────────────────────────────────────────
# Admin — Update Temple
# PUT /{id}
# All fields optional — only update what is sent
# ─────────────────────────────────────────────
class TempleUpdate(BaseModel):
    name:           Optional[str]   = None
    description:    Optional[str]   = None
    deity:          Optional[str]   = None
    district:       Optional[str]   = None
    address:        Optional[str]   = None
    latitude:       Optional[float] = None
    longitude:      Optional[float] = None
    dress_code:     Optional[str]   = None
    contact_number: Optional[str]   = None
    website:        Optional[str]   = None
    is_featured:    Optional[bool]  = None
    timings:        Optional[Dict[str, Any]] = None
    images:         Optional[List[str]]      = None
    is_active:      Optional[bool]  = None


# ─────────────────────────────────────────────
# Temple Event Response
# GET /{id}/events
# ─────────────────────────────────────────────
class TempleEventResponse(BaseModel):
    id:          UUID
    temple_id:   UUID
    name:        str
    description: Optional[str] = None
    event_date:  date
    start_time:  Optional[time] = None
    end_time:    Optional[time] = None
    is_active:   bool
    created_at:  datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# Temple Review Schemas
# GET /{id}/reviews
# ─────────────────────────────────────────────
class TempleReviewCreate(BaseModel):
    rating:     float = Field(..., ge=1.0, le=5.0)
    title:      Optional[str]  = None
    body:       Optional[str]  = None
    visit_date: Optional[date] = None


class TempleReviewResponse(BaseModel):
    id:          UUID
    temple_id:   UUID
    user_id:     UUID
    rating:      float
    title:       Optional[str]  = None
    body:        Optional[str]  = None
    visit_date:  Optional[date] = None
    is_verified: bool
    created_at:  datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# Temple List Item
# GET / — includes total_slots_available_today
# ─────────────────────────────────────────────
class TempleListItem(BaseModel):
    id:                         UUID
    name:                       str
    deity:                      str
    district:                   str
    address:                    Optional[str]       = None
    latitude:                   Optional[float]     = None
    longitude:                  Optional[float]     = None
    is_featured:                bool
    booking_count:              int                 = 0
    images:                     Optional[List[str]] = []
    total_slots_available_today: int                = 0

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# Temple Detail
# GET /{id} — full detail with events and reviews
# ─────────────────────────────────────────────
class TempleDetail(BaseModel):
    id:             UUID
    name:           str
    description:    Optional[str]   = None
    deity:          str
    district:       str
    address:        Optional[str]   = None
    latitude:       Optional[float] = None
    longitude:      Optional[float] = None
    dress_code:     Optional[str]   = None
    contact_number: Optional[str]   = None
    website:        Optional[str]   = None
    timings:        Optional[Dict[str, Any]]    = None
    images:         Optional[List[str]]         = []
    is_featured:    bool
    booking_count:  int                         = 0
    is_active:      bool
    created_at:     datetime
    updated_at:     datetime
    events:         Optional[List[TempleEventResponse]]  = []
    reviews:        Optional[List[TempleReviewResponse]] = []

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# Timings Response
# GET /{id}/timings
# ─────────────────────────────────────────────
class TempleTimingsResponse(BaseModel):
    temple_id: UUID
    name:      str
    timings:   Optional[Dict[str, Any]] = None

    model_config = {"from_attributes": True}

class PoojaServiceCreate(BaseModel):
    name: str
    price: float
    duration_minutes: int | None = None
    description: str | None = None


class PoojaServiceUpdate(BaseModel):
    name: str | None = None
    price: float | None = None
    duration_minutes: int | None = None
    description: str | None = None

class TempleEventCreate(BaseModel):
    name: str
    description: Optional[str] = None
    event_date: date
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    is_active: bool = True