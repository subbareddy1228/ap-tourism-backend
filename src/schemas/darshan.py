from __future__ import annotations
from datetime import datetime, date, time
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel

from src.models.temple import DarshanType, BookingStatus


# ─────────────────────────────────────────────
# Darshan Type Schemas
# ─────────────────────────────────────────────

class DarshanTypeResponse(BaseModel):
    id: UUID
    temple_id: UUID
    name: str
    darshan_type: DarshanType
    description: Optional[str] = None
    price: float
    duration_minutes: int
    max_persons_per_booking: int
    is_active: bool

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# Darshan Slot Schemas
# ─────────────────────────────────────────────

class DarshanSlotResponse(BaseModel):
    id: UUID
    temple_id: UUID
    darshan_type_id: UUID
    slot_date: date
    start_time: time
    end_time: time
    total_quota: int
    booked_count: int
    available_quota: int
    is_active: bool

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# Darshan Booking Schemas
# ─────────────────────────────────────────────

class DarshanCheckAvailabilityRequest(BaseModel):
    slot_id: UUID
    num_persons: int = 1


class DarshanCheckAvailabilityResponse(BaseModel):
    slot_id: UUID
    available: bool
    available_quota: int
    message: str


class PilgrimDetail(BaseModel):
    name: str
    age: int
    id_proof: Optional[str] = None


class DarshanBookRequest(BaseModel):
    slot_id: UUID
    num_persons: int = 1
    pilgrim_details: Optional[List[PilgrimDetail]] = []


class DarshanBookingResponse(BaseModel):
    id: UUID
    temple_id: UUID
    slot_id: UUID
    user_id: UUID
    booking_reference: str
    num_persons: int
    total_amount: float
    status: BookingStatus
    payment_id: Optional[str] = None
    qr_code: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# Pooja Service Schemas
# ─────────────────────────────────────────────

class PoojaServiceResponse(BaseModel):
    id: UUID
    temple_id: UUID
    name: str
    description: Optional[str] = None
    price: float
    duration_minutes: int
    max_persons: int
    requires_priest: bool
    is_active: bool

    class Config:
        from_attributes = True


class PoojaSlotResponse(BaseModel):
    id: UUID
    service_id: UUID
    slot_date: date
    start_time: time
    end_time: time
    total_quota: int
    booked_count: int
    is_active: bool

    class Config:
        from_attributes = True


class PoojaBookRequest(BaseModel):
    pooja_service_id: UUID
    slot_id: UUID
    num_persons: int = 1
    special_requests: Optional[str] = None


class PoojaBookingResponse(BaseModel):
    id: UUID
    temple_id: UUID
    service_id: UUID
    slot_id: UUID
    user_id: UUID
    booking_reference: str
    num_persons: int
    total_amount: float
    status: BookingStatus
    payment_id: Optional[str] = None
    special_requests: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# Prasadam Schemas
# ─────────────────────────────────────────────

class PrasadamItemResponse(BaseModel):
    id: UUID
    temple_id: UUID
    name: str
    description: Optional[str] = None
    price: float
    weight_grams: Optional[int] = None
    is_available: bool
    image_url: Optional[str] = None

    class Config:
        from_attributes = True


class PrasadamOrderItemRequest(BaseModel):
    item_id: UUID
    quantity: int = 1


class PrasadamOrderRequest(BaseModel):
    items: List[PrasadamOrderItemRequest]
    pickup_date: Optional[date] = None


class PrasadamOrderItemResponse(BaseModel):
    id: UUID
    item_id: UUID
    quantity: int
    unit_price: float
    subtotal: float

    class Config:
        from_attributes = True


class PrasadamOrderResponse(BaseModel):
    id: UUID
    temple_id: UUID
    user_id: UUID
    order_reference: str
    total_amount: float
    pickup_date: Optional[date] = None
    status: BookingStatus
    payment_id: Optional[str] = None
    items: List[PrasadamOrderItemResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True