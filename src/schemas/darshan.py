from __future__ import annotations
from datetime import datetime, date, time
from typing import Optional, List, Any
from uuid import UUID
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────
# Darshan Type Schemas
# GET /{id}/darshan-types
# GET /{id}/darshan-types/{type_id}
# ─────────────────────────────────────────────
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


# ─────────────────────────────────────────────
# Darshan Slot Schemas
# GET /{id}/darshan-slots
# GET /{id}/darshan-slots/{date}
# ─────────────────────────────────────────────
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


# ─────────────────────────────────────────────
# Check Availability
# POST /{id}/darshan/check-availability
# ─────────────────────────────────────────────
class DarshanCheckAvailabilityRequest(BaseModel):
    slot_id:     UUID
    num_persons: int = Field(..., ge=1, le=10)


class DarshanCheckAvailabilityResponse(BaseModel):
    slot_id:           UUID
    is_available:      bool
    available_count:   int
    requested_persons: int
    message:           str


# ─────────────────────────────────────────────
# Pilgrim Detail
# Used in darshan booking
# ─────────────────────────────────────────────
class PilgrimDetail(BaseModel):
    name:             str
    age:              int            = Field(..., ge=1, le=120)
    id_proof_type:    Optional[str]  = None   # AADHAR, PAN, PASSPORT, VOTER_ID, DRIVING_LICENSE
    id_proof_number:  Optional[str]  = None


# ─────────────────────────────────────────────
# Darshan Booking Schemas
# POST /{id}/darshan/book
# GET /{id}/darshan/booking/{booking_id}
# ─────────────────────────────────────────────
class DarshanBookRequest(BaseModel):
    slot_id:         UUID
    num_persons:     int                         = Field(..., ge=1, le=10)
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


# ─────────────────────────────────────────────
# Pooja Service Schemas
# GET /{id}/pooja-services
# GET /{id}/pooja-services/{id}
# ─────────────────────────────────────────────
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


# ─────────────────────────────────────────────
# Pooja Slot Schemas
# GET /{id}/pooja-services/{id}/slots
# ─────────────────────────────────────────────
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


# ─────────────────────────────────────────────
# Pooja Booking Schemas
# POST /{id}/pooja/book
# ─────────────────────────────────────────────
class PoojaBookRequest(BaseModel):
    pooja_service_id: UUID
    slot_id:          UUID
    num_persons:      int            = Field(default=1, ge=1)
    devotee_name:     Optional[str]  = None
    gotram:           Optional[str]  = None
    special_requests: Optional[str]  = None


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
    gotram:            Optional[str] = None
    special_requests:  Optional[str] = None
    created_at:        datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# Prasadam Schemas
# GET /{id}/prasadam
# GET /{id}/prasadam/{item_id}
# POST /{id}/prasadam/order
# GET /{id}/prasadam/orders
# ─────────────────────────────────────────────
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