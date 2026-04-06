"""
schemas/darshan.py  —  Temple / Darshan / Pooja / Prasadam Module Schemas
Pydantic v2

Changes vs original:
  PoojaBookRequest  — renamed gotram → gothram to match PoojaBooking model column.
  PoojaBookingResponse — renamed gotram → gothram for the same reason.
  Both schema classes were referencing req.gotram / orm.gotram which would
  cause AttributeError after the model rename is applied.
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Darshan Type ──────────────────────────────────────────────────────────────

class DarshanTypeResponse(BaseModel):
    id:                      UUID
    temple_id:               UUID
    name:                    str
    darshan_type:            str
    description:             Optional[str] = None
    price:                   float
    duration_minutes:        int
    what_is_included:        Optional[str] = None
    max_persons_per_booking: int
    is_active:               bool

    model_config = {"from_attributes": True}


# ── Darshan Slot ──────────────────────────────────────────────────────────────

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
    num_persons:     int                           = Field(..., ge=1, le=10)
    pilgrim_details: Optional[List[PilgrimDetail]] = []


class DarshanBookingResponse(BaseModel):
    id:                UUID
    temple_id:         UUID
    slot_id:           UUID
    user_id:           UUID
    booking_reference: str
    num_persons:       int
    total_amount:      float
    status:            str
    payment_id:        Optional[str]       = None
    qr_code:           Optional[str]       = None
    pilgrim_details:   Optional[List[Any]] = []
    created_at:        datetime

    model_config = {"from_attributes": True}


# ── Pooja Service ─────────────────────────────────────────────────────────────

class PoojaServiceResponse(BaseModel):
    id:                  UUID
    temple_id:           UUID
    name:                str
    description:         Optional[str] = None
    price:               float
    duration_minutes:    int
    items_included:      Optional[str] = None
    priest_requirements: Optional[str] = None
    max_persons:         int
    is_active:           bool

    model_config = {"from_attributes": True}


# ── Pooja Slot ────────────────────────────────────────────────────────────────

class PoojaSlotResponse(BaseModel):
    id:               UUID
    temple_id:        UUID
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


# ── Pooja Booking ─────────────────────────────────────────────────────────────

class PoojaBookRequest(BaseModel):
    pooja_service_id: UUID
    slot_id:          UUID
    num_persons:      int           = Field(default=1, ge=1)
    devotee_name:     Optional[str] = None
    gothram:          Optional[str] = None   # Fixed: was gotram (spelling mismatch with model)
    special_requests: Optional[str] = None


class PoojaBookingResponse(BaseModel):
    id:                UUID
    temple_id:         UUID
    pooja_service_id:  UUID
    slot_id:           UUID
    user_id:           UUID
    booking_reference: str
    num_persons:       int
    total_amount:      float
    status:            str
    payment_id:        Optional[str] = None
    devotee_name:      Optional[str] = None
    gothram:           Optional[str] = None   # Fixed: was gotram
    special_requests:  Optional[str] = None
    created_at:        datetime

    model_config = {"from_attributes": True}


# ── Prasadam ──────────────────────────────────────────────────────────────────

class PrasadamItemResponse(BaseModel):
    id:           UUID
    temple_id:    UUID
    name:         str
    description:  Optional[str] = None
    price:        float
    weight_grams: Optional[int] = None
    image_url:    Optional[str] = None
    is_available: bool

    model_config = {"from_attributes": True}


class PrasadamOrderItemRequest(BaseModel):
    item_id:  UUID
    quantity: int = Field(default=1, ge=1)


class PrasadamOrderRequest(BaseModel):
    items:       List[PrasadamOrderItemRequest]
    pickup_date: Optional[date] = None


class PrasadamOrderItemResponse(BaseModel):
    id:         UUID
    item_id:    UUID
    quantity:   int
    unit_price: float
    subtotal:   float

    model_config = {"from_attributes": True}


class PrasadamOrderResponse(BaseModel):
    id:              UUID
    temple_id:       UUID
    user_id:         UUID
    order_reference: str
    total_amount:    float
    pickup_date:     Optional[date] = None
    status:          str
    payment_id:      Optional[str]  = None
    items:           List[PrasadamOrderItemResponse] = []
    created_at:      datetime

    model_config = {"from_attributes": True}