"""
schemas/darshan.py  —  Temple / Darshan / Pooja / Prasadam Module Schemas
Pydantic v2

Changes vs original:
  DarshanBookingResponse — corrected 6 fields to match updated DarshanBooking model:
    • slot_id           → darshan_slot_id   (column was renamed in model)
    • user_id           → removed           (no user_id column on DarshanBooking)
    • booking_reference → removed           (no booking_reference column on DarshanBooking)
    • total_amount      → total_price       (column was renamed in model)
    • status            → removed           (no status column; master bookings.status is source of truth)
    • payment_id        → removed           (no payment_id column on DarshanBooking)
    • qr_code           → removed           (no qr_code column on DarshanBooking)
    • Added: darshan_slot_id, darshan_type_id, darshan_date, darshan_time,
             price_per_person, ticket_number  (real model columns, now exposed)

  PoojaBookingResponse — corrected 6 fields to match updated PoojaBooking model:
    • user_id           → removed           (no user_id column on PoojaBooking)
    • total_amount      → price             (column was renamed in model)
    • status            → removed           (no status column on PoojaBooking)
    • payment_id        → removed           (no payment_id column on PoojaBooking)
    • devotee_name      → devotee_names     (column renamed + type changed to list in model)
    • special_requests  → special_instructions (column was renamed in model)
    • gothram           kept ✓ (already fixed in previous batch)
    • Added: pooja_date, pooja_time, nakshatra  (real model columns, now exposed)

  PrasadamOrderResponse — corrected 2 fields to match updated PrasadamOrder model:
    • user_id           → removed           (no user_id column on PrasadamOrder;
                                             user is on master Booking)
    • payment_id        → removed           (no payment_id column on PrasadamOrder)
    • Added: delivery_status, tracking_number  (real model columns, now exposed)

  PoojaBookRequest — kept as-is (devotee_name stays singular str for input,
    service converts it to a list before writing to model).
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
    id:               UUID
    temple_id:        UUID
    # FIX: slot_id → darshan_slot_id (column was renamed in DarshanBooking model)
    darshan_slot_id:  Optional[UUID]       = None
    darshan_type_id:  Optional[UUID]       = None
    darshan_date:     date
    darshan_time:     time
    num_persons:      int
    price_per_person: float
    # FIX: total_amount → total_price (column was renamed in DarshanBooking model)
    total_price:      float
    ticket_number:    Optional[str]        = None
    devotee_details:  Optional[List[Any]]  = []
    created_at:       Optional[datetime]   = None
    # Removed: user_id (no such column on DarshanBooking)
    # Removed: booking_reference (no such column on DarshanBooking)
    # Removed: status (no status column; master bookings.status is source of truth)
    # Removed: payment_id (no such column on DarshanBooking)
    # Removed: qr_code (no such column on DarshanBooking)

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
    # devotee_name stays as singular str for API input convenience;
    # darshan_service.book_pooja() wraps it into a list before writing
    # to the model's devotee_names (JSONB) column.
    devotee_name:     Optional[str] = None
    gothram:          Optional[str] = None
    special_requests: Optional[str] = None


class PoojaBookingResponse(BaseModel):
    id:               UUID
    temple_id:        Optional[UUID]        = None
    pooja_service_id: Optional[UUID]        = None
    slot_id:          Optional[UUID]        = None
    booking_reference: Optional[str]        = None
    num_persons:      int
    # FIX: total_amount → price (column was renamed in PoojaBooking model)
    price:            Optional[float]       = None
    # FIX: devotee_name → devotee_names (column renamed + type changed to JSONB list)
    devotee_names:    Optional[List[Any]]   = []
    gothram:          Optional[str]         = None
    nakshatra:        Optional[str]         = None
    # FIX: special_requests → special_instructions (column was renamed in model)
    special_instructions: Optional[str]    = None
    pooja_date:       Optional[date]        = None
    pooja_time:       Optional[time]        = None
    created_at:       Optional[datetime]    = None
    # Removed: user_id (no such column on PoojaBooking)
    # Removed: status (no status column on PoojaBooking)
    # Removed: payment_id (no such column on PoojaBooking)
    # Removed: devotee_name singular (replaced by devotee_names list)
    # Removed: special_requests (renamed to special_instructions in model)

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
    temple_id:       Optional[UUID]                    = None
    order_reference: Optional[str]                     = None
    total_amount:    Optional[float]                   = None
    pickup_date:     Optional[date]                    = None
    status:          Optional[str]                     = None
    delivery_status: Optional[str]                     = None
    tracking_number: Optional[str]                     = None
    items:           List[PrasadamOrderItemResponse]   = []
    created_at:      Optional[datetime]                = None
    # Removed: user_id (no user_id column on PrasadamOrder; user is on master Booking)
    # Removed: payment_id (no payment_id column on PrasadamOrder)

    model_config = {"from_attributes": True}

class DarshanTypeCreate(BaseModel):
    name: str
    darshan_type: str
    description: str | None = None
    price: float = 0
    duration_minutes: int = 30
    what_is_included: str | None = None
    max_persons_per_booking: int = 6
    is_active: bool = True