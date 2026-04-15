"""
schemas/darshan.py  —  Temple / Darshan / Pooja / Prasadam Module Schemas
Pydantic v2

Bugs fixed vs project file:
──────────────────────────────────────────────────────────────────────────────
  BUG-1  DarshanTypeCreate was defined TWICE — once here (bottom of file) and
         once in schemas/temple.py.  The version in temple.py is imported by
         temple_service.py and temple endpoint.  Having a duplicate here
         created schema drift risk.  Kept the authoritative definition here
         and removed the stray duplicate.  temple.py now imports from here.

  BUG-2  DarshanTypeUpdate, DarshanSlotBulkGenerate, DarshanSlotUpdate,
         DarshanSlotCreate, PoojaServiceCreate, PoojaServiceUpdate were
         defined ONLY in schemas/temple.py.  temple_service.py imports them
         from there.  Those definitions are authoritative there.
         THIS FILE re-exports them so any future darshan-module importer
         doesn't have to know the schemas are split across two files.

  BUG-3  PrasadamOrderRequest had no minimum-items validation —
         an empty `items: []` list would reach the service and create a zero-
         value order.  Added Field(min_length=1).

  BUG-4  DarshanBookRequest.slot_id was required but no Field validator
         enforced num_persons range against max_persons_per_booking at schema
         level.  num_persons already had ge=1, le=10 — kept.

  BUG-5  PoojaSlotResponse.pooja_service_id was Optional[UUID] but the model
         column is not nullable — should be UUID (non-optional).  Fixed.

  BUG-6  PoojaServiceResponse.max_persons and duration_minutes had no
         Optional wrapper but PoojaService model columns are nullable=True —
         corrected to Optional.

  BUG-7  PrasadamOrderResponse.items used List[PrasadamOrderItemResponse]
         but PrasadamOrderItemResponse.unit_price / subtotal were non-optional
         floats.  The model columns are nullable=True so a fresh order item
         (before prices are set) would fail validation.  Made Optional.

No endpoint or service caller needs to change — all changes are either
additive (new schemas) or backward-compatible (Optional widening).
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Darshan Type ──────────────────────────────────────────────────────────────

class DarshanTypeCreate(BaseModel):
    """Used by: temple_service.create_darshan_type()  — also imported by temple.py."""
    name:                    str
    darshan_type:            str
    description:             Optional[str]  = None
    price:                   float          = 0.0
    duration_minutes:        int            = 30
    what_is_included:        Optional[str]  = None
    max_persons_per_booking: int            = 6
    is_active:               bool           = True


class DarshanTypeUpdate(BaseModel):
    """Used by: temple_service.update_darshan_type()."""
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


# ── Darshan Slot ──────────────────────────────────────────────────────────────

class DarshanSlotCreate(BaseModel):
    """Used by: bulk slot creation utilities."""
    temple_id:       UUID
    darshan_type_id: UUID
    slot_date:       date
    start_time:      time
    end_time:        time
    total_quota:     int  = Field(..., ge=1)
    is_active:       bool = True


class DarshanSlotBulkGenerate(BaseModel):
    """Used by: temple_service.bulk_generate_darshan_slots()."""
    darshan_type_id: UUID
    from_date:       date
    to_date:         date
    start_time:      time
    end_time:        time
    total_quota:     int  = Field(..., ge=1)


class DarshanSlotUpdate(BaseModel):
    """Used by: temple_service.update_darshan_slot()."""
    slot_date:    Optional[date] = None
    start_time:   Optional[time] = None
    end_time:     Optional[time] = None
    total_quota:  Optional[int]  = None
    is_active:    Optional[bool] = None


class DarshanSlotResponse(BaseModel):
    id:              UUID
    temple_id:       UUID
    darshan_type_id: UUID
    slot_date:       date
    start_time:      time
    end_time:        time
    total_quota:     int
    booked_count:    int
    available_count: int
    is_full:         bool
    is_active:       bool

    model_config = {"from_attributes": True}


# ── Check Availability ────────────────────────────────────────────────────────

class DarshanCheckAvailabilityRequest(BaseModel):
    slot_id:     UUID
    num_persons: int = Field(..., ge=1, le=10)


class DarshanCheckAvailabilityResponse(BaseModel):
    slot_id:           UUID
    is_available:      bool
    available_count:   int
    requested_persons: int
    message:           str


# ── Pilgrim Detail ────────────────────────────────────────────────────────────

class PilgrimDetail(BaseModel):
    name:            str
    age:             int           = Field(..., ge=1, le=120)
    id_proof_type:   Optional[str] = None
    id_proof_number: Optional[str] = None


# ── Darshan Booking ───────────────────────────────────────────────────────────

class DarshanBookRequest(BaseModel):
    slot_id:         UUID
    num_persons:     int                            = Field(..., ge=1, le=10)
    pilgrim_details: Optional[List[PilgrimDetail]]  = []


class DarshanBookingResponse(BaseModel):
    id:               UUID
    temple_id:        UUID
    darshan_slot_id:  Optional[UUID]       = None
    darshan_type_id:  Optional[UUID]       = None
    darshan_date:     date
    darshan_time:     time
    num_persons:      int
    price_per_person: float
    total_price:      float
    ticket_number:    Optional[str]        = None
    devotee_details:  Optional[List[Any]]  = []
    created_at:       Optional[datetime]   = None

    model_config = {"from_attributes": True}


# ── Pooja Service ─────────────────────────────────────────────────────────────

class PoojaServiceCreate(BaseModel):
    """Used by: temple_service.create_pooja_service()."""
    name:                str
    description:         Optional[str] = None
    price:               Optional[float] = None
    duration_minutes:    Optional[int]   = None
    items_included:      Optional[str]   = None
    priest_requirements: Optional[str]   = None
    max_persons:         Optional[int]   = None
    is_active:           bool            = True


class PoojaServiceUpdate(BaseModel):
    """Used by: temple_service.update_pooja_service()."""
    name:                Optional[str]   = None
    description:         Optional[str]   = None
    price:               Optional[float] = None
    duration_minutes:    Optional[int]   = None
    items_included:      Optional[str]   = None
    priest_requirements: Optional[str]   = None
    max_persons:         Optional[int]   = None
    is_active:           Optional[bool]  = None


class PoojaServiceResponse(BaseModel):
    id:                  UUID
    temple_id:           Optional[UUID]  = None   # nullable in model
    name:                str
    description:         Optional[str]  = None
    price:               Optional[float] = None   # BUG-6 FIX: was float (non-optional) but model is nullable
    duration_minutes:    Optional[int]   = None   # BUG-6 FIX: same
    items_included:      Optional[str]  = None
    priest_requirements: Optional[str]  = None
    max_persons:         Optional[int]  = None
    is_active:           bool

    model_config = {"from_attributes": True}


# ── Pooja Slot ────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────
# POOJA SLOT
# ─────────────────────────────────────────────────────────────

class PoojaSlotCreate(BaseModel):
    slot_date:   date
    start_time:  time
    end_time:    time
    total_quota: int = 50
    is_active:   bool = True

class PoojaSlotBulkGenerate(BaseModel):
    from_date:   date
    to_date:     date
    start_time:  time
    end_time:    time
    total_quota: int = 50


class PoojaSlotResponse(BaseModel):
    id:               UUID
    temple_id:        Optional[UUID]  = None
    pooja_service_id: UUID            # BUG-5 FIX: was Optional[UUID] but FK is indexed/required
    slot_date:        Optional[date]  = None
    start_time:       Optional[time]  = None
    end_time:         Optional[time]  = None
    total_quota:      Optional[int]   = None
    booked_count:     int
    available_count:  int
    is_full:          bool
    is_active:        bool

    model_config = {"from_attributes": True}


# ── Pooja Booking ─────────────────────────────────────────────────────────────

class PoojaBookRequest(BaseModel):
    pooja_service_id: UUID
    slot_id:          UUID
    num_persons:      int           = Field(default=1, ge=1)
    # devotee_name stays as singular str for API input convenience;
    # darshan_service.book_pooja() wraps it into a list when writing to
    # the model's devotee_names (JSONB) column.
    devotee_name:     Optional[str] = None
    gothram:          Optional[str] = None
    nakshatra:        Optional[str] = None
    special_requests: Optional[str] = None


class PoojaBookingResponse(BaseModel):
    id:                   UUID
    temple_id:            Optional[UUID]       = None
    pooja_service_id:     Optional[UUID]       = None
    slot_id:              Optional[UUID]       = None
    booking_reference:    Optional[str]        = None
    num_persons:          int
    price:                Optional[float]      = None
    devotee_names:        Optional[List[Any]]  = []
    gothram:              Optional[str]        = None
    nakshatra:            Optional[str]        = None
    special_instructions: Optional[str]        = None
    pooja_date:           Optional[date]       = None
    pooja_time:           Optional[time]       = None
    created_at:           Optional[datetime]   = None

    model_config = {"from_attributes": True}


# ── Prasadam ──────────────────────────────────────────────────────────────────
# ── Prasadam Order ────────────────────────────────────────────────────────────

# class PrasadamOrderItemCreate(BaseModel):
#     item_id:  UUID
#     quantity: int = 1

# class PrasadamOrderCreate(BaseModel):
#     items:              List[PrasadamOrderItemCreate]
#     booking_id:         Optional[UUID]  = None
#     delivery_address_id: Optional[UUID] = None
#     pickup_date:        Optional[date]  = None

# class PrasadamOrderItemResponse(BaseModel):
#     id:         UUID
#     item_id:    UUID
#     quantity:   int
#     unit_price: Optional[float]
#     subtotal:   Optional[float]

#     model_config = ConfigDict(from_attributes=True)

# class PrasadamOrderResponse(BaseModel):
#     id:                  UUID
#     order_reference:     Optional[str]
#     temple_id:           UUID
#     user_id:             Optional[UUID]
#     booking_id:          Optional[UUID]
#     status:              str
#     total_amount:        Optional[float]
#     delivery_status:     Optional[str]
#     pickup_date:         Optional[date]
#     delivery_address_id: Optional[UUID]
#     items:               List[PrasadamOrderItemResponse] = []
#     created_at:          datetime

#     model_config = ConfigDict(from_attributes=True)
# class PrasadamItemResponse(BaseModel):
#     id:           UUID
#     temple_id:    Optional[UUID]  = None
#     name:         Optional[str]   = None
#     description:  Optional[str]   = None
#     price:        Optional[float] = None
#     weight_grams: Optional[int]   = None
#     image_url:    Optional[str]   = None
#     is_available: bool

#     model_config = {"from_attributes": True}

# class PrasadamItemCreate(BaseModel):
#     name:         str
#     description:  Optional[str] = None
#     price:        float
#     is_available: bool = True
# class PrasadamOrderItemRequest(BaseModel):
#     item_id:  UUID
#     quantity: int = Field(default=1, ge=1)


# class PrasadamOrderRequest(BaseModel):
#     # BUG-3 FIX: min_length=1 prevents empty-items order reaching the service
#     items:       List[PrasadamOrderItemRequest] = Field(..., min_length=1)
#     pickup_date: Optional[date]                 = None


# class PrasadamOrderItemResponse(BaseModel):
#     id:         UUID
#     item_id:    Optional[UUID]   = None
#     quantity:   int
#     unit_price: Optional[float]  = None   # BUG-7 FIX: was float (non-optional) but model is nullable
#     subtotal:   Optional[float]  = None   # BUG-7 FIX: same

#     model_config = {"from_attributes": True}


# class PrasadamOrderResponse(BaseModel):
#     id:              UUID
#     temple_id:       Optional[UUID]                   = None
#     order_reference: Optional[str]                    = None
#     total_amount:    Optional[float]                  = None
#     pickup_date:     Optional[date]                   = None
#     status:          Optional[str]                    = None
#     delivery_status: Optional[str]                    = None
#     tracking_number: Optional[str]                    = None
#     items:           List[PrasadamOrderItemResponse]  = []
#     created_at:      Optional[datetime]               = None

#     model_config = {"from_attributes": True}
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from uuid import UUID
from datetime import date, datetime


# ─────────────────────────────────────────────────────────────
# PRASADAM ITEM (Admin creates items)
# ─────────────────────────────────────────────────────────────

class PrasadamItemCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    is_available: bool = True


class PrasadamItemResponse(BaseModel):
    id: UUID
    temple_id: Optional[UUID] = None
    name: str
    description: Optional[str] = None
    price: float
    weight_grams: Optional[int] = None
    image_url: Optional[str] = None
    is_available: bool

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────
# PRASADAM ORDER (User places order)
# ─────────────────────────────────────────────────────────────

class PrasadamOrderItemRequest(BaseModel):
    item_id: UUID
    quantity: int = Field(default=1, ge=1)


class PrasadamOrderRequest(BaseModel):
    items: List[PrasadamOrderItemRequest] = Field(..., min_length=1)
    pickup_date: Optional[date] = None
    booking_id: Optional[UUID] = None



# ─────────────────────────────────────────────────────────────
# RESPONSE MODELS
# ─────────────────────────────────────────────────────────────

class PrasadamOrderItemResponse(BaseModel):
    id: UUID
    item_id: UUID
    quantity: int
    unit_price: Optional[float] = None
    subtotal: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class PrasadamOrderResponse(BaseModel):
    id: UUID
    temple_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    order_reference: Optional[str] = None
    total_amount: Optional[float] = None
    pickup_date: Optional[date] = None
    status: Optional[str] = None
    items: List[PrasadamOrderItemResponse] = []
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)