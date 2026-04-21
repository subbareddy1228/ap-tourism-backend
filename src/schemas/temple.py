"""
schemas/temple.py  —  Temple Module Pydantic Schemas
Pydantic v2 — model_config used throughout.

Changes vs original:
  - Added DarshanTypeCreate and DarshanTypeUpdate schemas that were missing.
    The endpoint was accepting raw `dict` for darshan type operations,
    which bypasses validation and has no OpenAPI documentation.
  - Added DarshanSlotUpdate schema for the update_darshan_slot endpoint.
  - Added TempleEventUpdate as an explicit update schema (was reusing Create,
    which makes all fields required on update).
  - PoojaServiceCreate / PoojaServiceUpdate already correct — unchanged.
  - All response schemas already correct — unchanged.
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# Temple Base / Create / Update
# ─────────────────────────────────────────────────────────────────────────────

class TempleBase(BaseModel):
    name:           str
    description:    Optional[str]            = None
    deity:          str
    district:       str
    address:        Optional[str]            = None
    latitude:       Optional[float]          = None
    longitude:      Optional[float]          = None
    dress_code:     Optional[str]            = None
    contact_number: Optional[str]            = None
    website:        Optional[str]            = None
    timings:        Optional[Dict[str, Any]] = None
    images:         Optional[List[str]]      = []


class TempleCreate(TempleBase):
    """POST /temples/ — Admin: add a new temple."""
    is_featured: Optional[bool] = False
    is_active:   Optional[bool] = True


class TempleUpdate(BaseModel):
    """PUT /temples/{id} — Admin: partial update, all fields optional."""
    name:           Optional[str]            = None
    description:    Optional[str]            = None
    deity:          Optional[str]            = None
    district:       Optional[str]            = None
    address:        Optional[str]            = None
    latitude:       Optional[float]          = None
    longitude:      Optional[float]          = None
    dress_code:     Optional[str]            = None
    contact_number: Optional[str]            = None
    website:        Optional[str]            = None
    is_featured:    Optional[bool]           = None
    is_active:      Optional[bool]           = None
    timings:        Optional[Dict[str, Any]] = None
    images:         Optional[List[str]]      = None


# ─────────────────────────────────────────────────────────────────────────────
# Temple List Item  (GET /)
# ─────────────────────────────────────────────────────────────────────────────

class TempleListItem(BaseModel):
    """Single row returned by list, featured, popular, nearby, by-deity, by-district."""
    id:                          UUID
    name:                        str
    deity:                       str
    district:                    str
    address:                     Optional[str]       = None
    latitude:                    Optional[float]     = None
    longitude:                   Optional[float]     = None
    is_featured:                 bool
    booking_count:               int                 = 0
    images:                      Optional[List[str]] = []
    total_slots_available_today: int                 = 0

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Temple Event Schemas
# ─────────────────────────────────────────────────────────────────────────────

class TempleEventCreate(BaseModel):
    """POST /temples/{id}/events — Admin: create a new event."""
    name:        str
    description: Optional[str]  = None
    event_date:  date
    start_time:  Optional[time] = None
    end_time:    Optional[time] = None
    is_active:   bool           = True


class TempleEventUpdate(BaseModel):
    """PUT /temples/{id}/events/{event_id} — Admin: partial update, all fields optional."""
    name:        Optional[str]  = None
    description: Optional[str]  = None
    event_date:  Optional[date] = None
    start_time:  Optional[time] = None
    end_time:    Optional[time] = None
    is_active:   Optional[bool] = None


class TempleEventResponse(BaseModel):
    id:          UUID
    temple_id:   UUID
    name:        str
    description: Optional[str]  = None
    event_date:  date
    start_time:  Optional[time] = None
    end_time:    Optional[time] = None
    is_active:   bool
    created_at:  datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Temple Review Schemas
# ─────────────────────────────────────────────────────────────────────────────

class TempleReviewCreate(BaseModel):
    """POST /temples/{id}/reviews — Authenticated user: submit a review."""
    rating:     float          = Field(..., ge=1.0, le=5.0)
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


# ─────────────────────────────────────────────────────────────────────────────
# Temple Detail  (GET /{id})
# ─────────────────────────────────────────────────────────────────────────────

class TempleDetail(BaseModel):
    """Full temple detail including events and reviews."""
    id:             UUID
    name:           str
    description:    Optional[str]                         = None
    deity:          str
    district:       str
    address:        Optional[str]                         = None
    latitude:       Optional[float]                       = None
    longitude:      Optional[float]                       = None
    dress_code:     Optional[str]                         = None
    contact_number: Optional[str]                         = None
    website:        Optional[str]                         = None
    timings:        Optional[Dict[str, Any]]              = None
    images:         Optional[List[str]]                   = []
    is_featured:    bool
    booking_count:  int                                   = 0
    is_active:      bool
    created_at:     datetime
    updated_at:     datetime
    events:         Optional[List[TempleEventResponse]]   = []
    reviews:        Optional[List[TempleReviewResponse]]  = []

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Timings  (GET /{id}/timings)
# ─────────────────────────────────────────────────────────────────────────────

class TempleTimingsResponse(BaseModel):
    temple_id: UUID
    name:      str
    timings:   Optional[Dict[str, Any]] = None

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Darshan Type Schemas  (previously missing — endpoints used raw dict)
# ─────────────────────────────────────────────────────────────────────────────

class DarshanTypeCreate(BaseModel):
    """POST /temples/{id}/darshan-types — Admin: add a darshan type."""
    name:                    str
    darshan_type:            str   = Field(..., description="e.g. FREE | VIP | SPECIAL")
    description:             Optional[str]  = None
    price:                   float          = 0.0
    duration_minutes:        int            = 30
    what_is_included:        Optional[str]  = None
    max_persons_per_booking: int            = Field(6, ge=1)
    is_active:               bool           = True


class DarshanTypeUpdate(BaseModel):
    """PUT /temples/{id}/darshan-types/{type_id} — Admin: partial update."""
    name:                    Optional[str]   = None
    darshan_type:            Optional[str]   = None
    description:             Optional[str]   = None
    price:                   Optional[float] = None
    duration_minutes:        Optional[int]   = None
    what_is_included:        Optional[str]   = None
    max_persons_per_booking: Optional[int]   = None
    is_active:               Optional[bool]  = None


class DarshanTypeResponse(BaseModel):
    id:                      UUID
    temple_id:               UUID
    name:                    str
    darshan_type:            str
    description:             Optional[str]  = None
    price:                   float
    duration_minutes:        int
    what_is_included:        Optional[str]  = None
    max_persons_per_booking: int
    is_active:               bool

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Darshan Slot Schemas  (previously missing typed update schema)
# ─────────────────────────────────────────────────────────────────────────────

class DarshanSlotBulkGenerate(BaseModel):
    """POST /temples/{id}/darshan-slots/bulk-generate — Admin."""
            
    darshan_type_id: UUID
    from_date: date
    to_date: date
    start_time: time
    end_time: time
    total_quota: int


class DarshanSlotUpdate(BaseModel):
    """PUT /temples/{id}/darshan-slots/{slot_id} — Admin: partial update."""
    start_time:  Optional[str]  = None
    end_time:    Optional[str]  = None
    total_quota: Optional[int]  = Field(None, ge=1)
    is_active:   Optional[bool] = None


class DarshanSlotResponse(BaseModel):
    id:           UUID
    temple_id:    UUID
    darshan_type_id: Optional[UUID] = None
    slot_date:    date
    start_time:   str
    end_time:     str
    total_quota:  int
    booked_count: int
    is_active:    bool

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Pooja Service Schemas
# ─────────────────────────────────────────────────────────────────────────────

class PoojaServiceCreate(BaseModel):
    """POST /temples/{id}/pooja-services — Admin: add a pooja service."""
    name:             str
    price:            float
    duration_minutes: Optional[int] = None
    description:      Optional[str] = None
    max_persons:      Optional[int] = None
    is_active:        bool          = True


class PoojaServiceUpdate(BaseModel):
    """PUT /temples/{id}/pooja-services/{service_id} — Admin: partial update."""
    name:             Optional[str]   = None
    price:            Optional[float] = None
    duration_minutes: Optional[int]   = None
    description:      Optional[str]   = None
    max_persons:      Optional[int]   = None
    is_active:        Optional[bool]  = None


class PoojaServiceResponse(BaseModel):
    id:               UUID
    temple_id:        UUID
    name:             str
    price:            float
    duration_minutes: Optional[int] = None
    description:      Optional[str] = None
    max_persons:      Optional[int] = None
    is_active:        bool

    model_config = {"from_attributes": True}


# ── Pooja Slot ────────────────────────────────────────────────────────────────

class PoojaSlotCreate(BaseModel):
    """POST /temples/{id}/pooja-services/{service_id}/slots — Admin: add a single slot."""
    slot_date:   date
    start_time:  time
    end_time:    time
    total_quota: int  = Field(..., ge=1)
    is_active:   bool = True


class PoojaSlotBulkGenerate(BaseModel):
    """POST /temples/{id}/pooja-services/{service_id}/slots/bulk-generate — Admin."""
    from_date:   date
    to_date:     date
    start_time:  time
    end_time:    time
    total_quota: int  = Field(..., ge=1)


class PoojaSlotUpdate(BaseModel):
    """PUT /temples/{id}/pooja-services/{service_id}/slots/{slot_id} — Admin: partial update."""
    slot_date:   Optional[date] = None
    start_time:  Optional[time] = None
    end_time:    Optional[time] = None
    total_quota: Optional[int]  = None
    is_active:   Optional[bool] = None


class PoojaSlotResponse(BaseModel):
    id:               UUID
    temple_id:        Optional[UUID] = None
    pooja_service_id: UUID
    slot_date:        date
    start_time:       time
    end_time:         time
    total_quota:      int
    booked_count:     int
    available_count:  int
    is_full:          bool
    is_active:        bool

    model_config = {"from_attributes": True}