from __future__ import annotations
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field
from src.models.temple import DarshanType, BookingStatus


# ── Darshan Type ──────────────────────────────────────────────────────────────
class DarshanTypeResponse(BaseModel):
    id: UUID
    temple_id: UUID
    name: DarshanType
    description: Optional[str]
    price: Decimal
    duration_minutes: Optional[int]
    what_is_included: Optional[str]
    is_active: bool

    model_config = {"from_attributes": True}


# ── Darshan Slot ──────────────────────────────────────────────────────────────
class DarshanSlotResponse(BaseModel):
    id: UUID
    temple_id: UUID
    darshan_type_id: UUID
    slot_date: date
    start_time: str
    end_time: str
    total_quota: int
    booked_count: int
    available_count: int
    is_full: bool

    model_config = {"from_attributes": True}


# ── Darshan Booking ───────────────────────────────────────────────────────────
class DarshanCheckAvailabilityRequest(BaseModel):
    slot_id: UUID
    devotees_count: int = Field(..., ge=1, le=10)


class DarshanCheckAvailabilityResponse(BaseModel):
    slot_id: UUID
    available: bool
    available_count: int
    requested_count: int
    message: str


class DarshanBookRequest(BaseModel):
    slot_id: UUID
    devotees_count: int = Field(..., ge=1, le=10)
    notes: Optional[str] = None


class DarshanBookingResponse(BaseModel):
    id: UUID
    temple_id: UUID
    slot_id: UUID
    user_id: UUID
    devotees_count: int
    status: BookingStatus
    total_amount: Decimal
    payment_id: Optional[str]
    qr_code: Optional[str]
    booking_reference: Optional[str]
    notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Pooja Service ─────────────────────────────────────────────────────────────
class PoojaServiceResponse(BaseModel):
    id: UUID
    temple_id: UUID
    name: str
    description: Optional[str]
    price: Decimal
    duration_minutes: Optional[int]
    items_included: Optional[str]
    priest_requirements: Optional[str]
    is_active: bool

    model_config = {"from_attributes": True}


class PoojaSlotResponse(BaseModel):
    id: UUID
    pooja_service_id: UUID
    slot_date: date
    start_time: str
    end_time: str
    total_quota: int
    booked_count: int
    available_count: int

    model_config = {"from_attributes": True}


class PoojaBookRequest(BaseModel):
    pooja_service_id: UUID       # FIX: caller must pass the service they want to book
    slot_id: UUID
    notes: Optional[str] = None


class PoojaBookingResponse(BaseModel):
    id: UUID
    pooja_service_id: UUID
    slot_id: UUID
    user_id: UUID
    status: BookingStatus
    total_amount: Optional[Decimal]
    payment_id: Optional[str]
    booking_reference: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Prasadam ──────────────────────────────────────────────────────────────────
class PrasadamItemResponse(BaseModel):
    id: UUID
    temple_id: UUID
    name: str
    description: Optional[str]
    price: Decimal
    image_url: Optional[str]
    is_available: bool

    model_config = {"from_attributes": True}


class PrasadamOrderItemRequest(BaseModel):
    prasadam_item_id: UUID
    quantity: int = Field(..., ge=1, le=20)


class PrasadamOrderRequest(BaseModel):
    items: List[PrasadamOrderItemRequest]
    pickup_date: Optional[date] = None


class PrasadamOrderItemResponse(BaseModel):
    id: UUID
    prasadam_item_id: UUID
    quantity: int
    unit_price: Decimal

    model_config = {"from_attributes": True}


class PrasadamOrderResponse(BaseModel):
    id: UUID
    temple_id: UUID
    user_id: UUID
    status: BookingStatus
    total_amount: Decimal
    payment_id: Optional[str]
    pickup_date: Optional[date]
    booking_reference: Optional[str]
    order_items: List[PrasadamOrderItemResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}