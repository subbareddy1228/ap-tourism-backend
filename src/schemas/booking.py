
"""
booking_schema.py  —  M11 Booking Module
Author  : LEV151 Shree Hari Pappaka
Module  : /api/v1/bookings

Cross-checked against:
  - Entity Relationship Diagram.drawio  (all request/response fields verified)
  - Booking Flow.drawio                 (BookingCreatedResponse fields)
  - Travel___Temple.xlsx                (M11 endpoint descriptions, Redis TTLs)
  - AP_Tourism_Backend API Specs.drawio (25 endpoints, cart, cancel, modify, invoice, ticket)
"""

from __future__ import annotations

from datetime import date, time, datetime
from decimal import Decimal
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from src.common.enums import (
    BookingType,
    BookingStatus,
    PaymentStatus,
    TripType,
    Gender,
    DeliveryStatus,
)


# ─────────────────────────────────────────────────────────────────────────────
# SHARED / NESTED SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class TravelerSchema(BaseModel):
    """Used inside any booking that carries traveler details."""
    name:            str              = Field(..., min_length=2, max_length=100)
    age:             int              = Field(..., ge=0, le=120)
    gender:          Optional[Gender] = None
    id_proof_type:   Optional[str]    = Field(None, description="AADHAAR | PAN | PASSPORT | VOTER_ID")
    id_proof_number: Optional[str]    = Field(None, max_length=100)
    is_primary:      bool             = False


class DevoteeDetail(BaseModel):
    """Devotee info for darshan / pooja bookings."""
    name:            str           = Field(..., min_length=2, max_length=100)
    age:             int           = Field(..., ge=0, le=120)
    id_proof_type:   Optional[str] = None
    id_proof_number: Optional[str] = None


class AddonSchema(BaseModel):
    addon_type:  str     = Field(..., description="travel_insurance | meal | photography | porterage")
    addon_name:  str     = Field(..., max_length=200)
    quantity:    int     = Field(1, ge=1)
    unit_price:  Decimal = Field(..., ge=0)
    total_price: Decimal = Field(..., ge=0)


class ContactDetailsSchema(BaseModel):
    name:  str                = Field(..., min_length=2, max_length=100)
    phone: str                = Field(..., pattern=r"^\+?[0-9]{10,13}$")
    email: Optional[EmailStr] = None   # EmailStr validates format e.g. user@example.com


class PaymentInfoSchema(BaseModel):
    """Payment snapshot embedded inside booking detail response."""
    transaction_id:      Optional[UUID]     = None
    razorpay_order_id:   Optional[str]      = None
    razorpay_payment_id: Optional[str]      = None
    payment_method:      Optional[str]      = None   # upi | card | netbanking | emi
    paid_at:             Optional[datetime] = None


# ─────────────────────────────────────────────────────────────────────────────
# CART SCHEMAS
# Redis key: cart:{user_id}  TTL: 1hr  (from Excel spec)
# ─────────────────────────────────────────────────────────────────────────────

class CartItemAddRequest(BaseModel):
    """POST /cart/add
    Excel: Add item to cart — {entity_type, entity_id, date, guests, options}.
    Validate availability first.
    """
    entity_type: BookingType    = Field(..., description="hotel | vehicle | darshan | package | guide")
    entity_id:   UUID           = Field(..., description="ID of the hotel / vehicle / temple / package / guide")
    date:        date           = Field(..., description="Travel / check-in / darshan date")
    guests:      int            = Field(1, ge=1, le=50)
    options:     Optional[dict] = Field(None, description="room_id | slot_id | trip_type | etc.")


class CartItemUpdateRequest(BaseModel):
    """PUT /cart/{item_id}
    Excel: Update cart item such as dates or guests count.
    """
    date:    Optional[date] = None
    guests:  Optional[int]  = Field(None, ge=1, le=50)
    options: Optional[dict] = None


class CartItemResponse(BaseModel):
    item_id:     str           # Redis key fragment — str is correct (Redis keys are strings)
    entity_type: BookingType
    entity_id:   UUID
    date:        date
    guests:      int
    options:     Optional[dict] = None
    added_at:    datetime


class CartResponse(BaseModel):
    """GET /cart
    Excel: Get current cart items stored in Redis per user (cart:{user_id}) with TTL 1hr.
    """
    user_id:    UUID
    items:      List[CartItemResponse]
    item_count: int
    expires_at: datetime   # cart:{user_id} Redis TTL 1hr


# ─────────────────────────────────────────────────────────────────────────────
# BOOKING LIST FILTER  (query params)
# ─────────────────────────────────────────────────────────────────────────────

class BookingListFilter(BaseModel):
    """Query parameters for GET /bookings/, GET /upcoming, GET /past, GET /cancelled.
    Excel: All bookings for user with filters status, type, date_range.
    """
    status:       Optional[BookingStatus] = None
    booking_type: Optional[BookingType]   = None   # renamed from `type` — avoids shadowing Python builtin
    date_from:    Optional[date]          = None
    date_to:      Optional[date]          = None
    page:         int                     = Field(1,  ge=1)
    per_page:     int                     = Field(10, ge=1, le=100)


# ─────────────────────────────────────────────────────────────────────────────
# CREATE BOOKING REQUEST SCHEMAS
# Slot lock: 15 min Redis TTL for all booking types (from Excel + Booking Flow diagram)
# ─────────────────────────────────────────────────────────────────────────────

class BookHotelRequest(BaseModel):
    """POST /bookings/hotel
    Excel: Book hotel room: {hotel_id, room_id, check_in, check_out, guests, special_requests}.
    Lock room 15 minutes in Redis.
    """
    hotel_id:         UUID
    room_id:          UUID
    check_in:         date
    check_out:        date
    rooms_count:      int                            = Field(1, ge=1, le=10)
    adults:           int                            = Field(1, ge=1, le=20)
    children:         int                            = Field(0, ge=0, le=10)
    special_requests: Optional[str]                  = Field(None, max_length=1000)
    contact_details:  Optional[ContactDetailsSchema] = None
    travelers:        Optional[List[TravelerSchema]] = None
    addons:           Optional[List[AddonSchema]]    = None
    coupon_code:      Optional[str]                  = Field(None, max_length=50)

    @field_validator("check_out")
    @classmethod
    def check_out_after_check_in(cls, v, info):
        if "check_in" in info.data and v <= info.data["check_in"]:
            raise ValueError("check_out must be after check_in")
        return v


class BookVehicleRequest(BaseModel):
    """POST /bookings/vehicle
    Excel: Book vehicle: {vehicle_id, pickup_date, pickup_address, drop_address, trip_type}.
    """
    vehicle_id:       UUID
    trip_type:        TripType
    pickup_date:      date
    pickup_address:   str               = Field(..., max_length=500)
    pickup_lat:       Optional[Decimal] = None
    pickup_lng:       Optional[Decimal] = None
    drop_address:     str               = Field(..., max_length=500)
    drop_lat:         Optional[Decimal] = None
    drop_lng:         Optional[Decimal] = None
    pickup_datetime:  datetime
    return_datetime:  Optional[datetime]             = None
    special_requests: Optional[str]                  = Field(None, max_length=1000)
    contact_details:  Optional[ContactDetailsSchema] = None
    travelers:        Optional[List[TravelerSchema]] = None
    addons:           Optional[List[AddonSchema]]    = None
    coupon_code:      Optional[str]                  = Field(None, max_length=50)

    @field_validator("return_datetime")
    @classmethod
    def return_after_pickup(cls, v, info):
        if v and "pickup_datetime" in info.data and v <= info.data["pickup_datetime"]:
            raise ValueError("return_datetime must be after pickup_datetime")
        return v


class BookDarshanRequest(BaseModel):
    """POST /bookings/darshan
    Excel: Book darshan slot with devotees list (name, age, id_proof).
    Booking Flow: Lock slot in Redis 15 min → create PENDING → trigger payment.
    """
    temple_id:        UUID
    darshan_slot_id:  UUID
    darshan_type_id:  UUID
    darshan_date:     date
    darshan_time:     Optional[time]                 = None   # slot has a specific time
    devotees:         List[DevoteeDetail]            = Field(..., min_length=1, max_length=20)
    special_requests: Optional[str]                  = Field(None, max_length=1000)
    contact_details:  Optional[ContactDetailsSchema] = None
    coupon_code:      Optional[str]                  = Field(None, max_length=50)


class BookPoojaRequest(BaseModel):
    """POST /bookings/pooja
    Excel: Book pooja service with devotees list.
    """
    pooja_service_id:     UUID
    pooja_date:           date
    pooja_time:           Optional[time]              = None
    devotee_names:        List[str]                   = Field(..., min_length=1, max_length=10)
    gothram:              Optional[str]               = Field(None, max_length=100)
    nakshatra:            Optional[str]               = Field(None, max_length=100)
    special_instructions: Optional[str]               = Field(None, max_length=1000)
    contact_details:      Optional[ContactDetailsSchema] = None
    coupon_code:          Optional[str]               = Field(None, max_length=50)


class PrasadamItemOrder(BaseModel):
    prasadam_item_id: UUID
    quantity:         int = Field(1, ge=1, le=50)


class BookPrasadamRequest(BaseModel):
    """POST /bookings/prasadam
    Excel: Order prasadam for pickup: {temple_id, items[], pickup_date}.
    """
    temple_id:           UUID
    items:               List[PrasadamItemOrder]      = Field(..., min_length=1)
    pickup_date:         date
    delivery_address_id: Optional[UUID]               = None   # None = pickup at temple
    contact_details:     Optional[ContactDetailsSchema] = None
    coupon_code:         Optional[str]                = Field(None, max_length=50)


class BookPackageRequest(BaseModel):
    """POST /bookings/package
    Excel: Book tour package with start_date, group_size, traveler_details.
    ERD:   package_bookings has start_date + end_date — both required.
    """
    package_id:       UUID
    start_date:       date
    end_date:         date                           # cross-checked: ERD package_bookings has end_date
    num_adults:       int                            = Field(1, ge=1, le=50)
    num_children:     int                            = Field(0, ge=0, le=20)
    customizations:   Optional[dict]                 = None   # {meals, room_type, extra_stops}
    traveler_details: Optional[List[TravelerSchema]] = None
    special_requests: Optional[str]                  = Field(None, max_length=1000)
    contact_details:  Optional[ContactDetailsSchema] = None
    addons:           Optional[List[AddonSchema]]    = None
    coupon_code:      Optional[str]                  = Field(None, max_length=50)

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, v, info):
        if "start_date" in info.data and v < info.data["start_date"]:
            raise ValueError("end_date must be on or after start_date")
        return v


class BookGuideRequest(BaseModel):
    """POST /bookings/guide
    Excel: Book guide with start_date, end_date, destination_id.
    """
    guide_id:           UUID
    start_date:         date
    end_date:           date
    destination_id:     UUID
    locations_to_cover: Optional[List[UUID]]          = None
    meeting_point:      Optional[str]                 = Field(None, max_length=500)
    special_requests:   Optional[str]                 = Field(None, max_length=1000)
    contact_details:    Optional[ContactDetailsSchema] = None
    coupon_code:        Optional[str]                 = Field(None, max_length=50)

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, v, info):
        if "start_date" in info.data and v < info.data["start_date"]:
            raise ValueError("end_date must be on or after start_date")
        return v


class BookComboRequest(BaseModel):
    """POST /bookings/combo
    Excel: Combo booking for package + hotel + vehicle in one transaction.
    At least one sub-booking is required.
    """
    package:          Optional[BookPackageRequest]   = None
    hotel:            Optional[BookHotelRequest]     = None
    vehicle:          Optional[BookVehicleRequest]   = None
    special_requests: Optional[str]                  = Field(None, max_length=1000)
    contact_details:  Optional[ContactDetailsSchema] = None
    coupon_code:      Optional[str]                  = Field(None, max_length=50)

    @model_validator(mode="after")
    def at_least_one_required(self):
        if not any([self.package, self.hotel, self.vehicle]):
            raise ValueError(
                "At least one of package, hotel, or vehicle is required for a combo booking"
            )
        return self


class BookCustomRequest(BaseModel):
    """POST /bookings/custom
    Excel: Custom trip request with destinations, dates, services_needed, group_size, budget.
    """
    destinations:     List[UUID]                     = Field(..., min_length=1)
    start_date:       date
    end_date:         date
    services_needed:  List[str]                      = Field(
                          ..., description="hotel | vehicle | guide | darshan | pooja"
                      )
    group_size:       int                            = Field(..., ge=1, le=100)
    budget:           Optional[Decimal]              = Field(None, ge=0)
    traveler_details: Optional[List[TravelerSchema]] = None
    special_requests: Optional[str]                  = Field(None, max_length=2000)
    contact_details:  Optional[ContactDetailsSchema] = None

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, v, info):
        if "start_date" in info.data and v < info.data["start_date"]:
            raise ValueError("end_date must be after start_date")
        return v


# ─────────────────────────────────────────────────────────────────────────────
# BOOKING CREATED RESPONSE
# Booking Flow diagram:
#   step 13 → {booking_id, amount, payment_required}
#   step 18 → {razorpay_order_id, key_id}
# Both returned together so client opens Razorpay checkout immediately.
# ─────────────────────────────────────────────────────────────────────────────

class BookingCreatedResponse(BaseModel):
    booking_id:        UUID
    booking_number:    str
    booking_type:      BookingType
    status:            BookingStatus
    payment_status:    PaymentStatus
    total_amount:      Decimal
    payment_required:  bool
    razorpay_order_id: Optional[str] = None   # Razorpay order to open checkout
    razorpay_key_id:   Optional[str] = None   # Razorpay public key for checkout
    message:           str


# ─────────────────────────────────────────────────────────────────────────────
# SUB-BOOKING DETAIL SCHEMAS
# Used inside BookingDetailResponse — one populated based on booking_type
# ─────────────────────────────────────────────────────────────────────────────

class HotelBookingDetail(BaseModel):
    id:                  UUID
    hotel_id:            UUID
    room_id:             UUID
    check_in_date:       date
    check_out_date:      date
    check_in_time:       Optional[time]
    check_out_time:      Optional[time]
    rooms_count:         int
    adults:              int
    children:            int
    room_rate_per_night: Decimal
    total_room_charge:   Decimal
    guest_details:       Optional[Any] = None

    model_config = {"from_attributes": True}


class VehicleBookingDetail(BaseModel):
    id:              UUID
    vehicle_id:      UUID
    driver_id:       Optional[UUID]
    trip_type:       TripType
    pickup_location: str
    drop_location:   str
    pickup_datetime: datetime
    return_datetime: Optional[datetime]
    estimated_km:    Optional[Decimal]
    actual_km:       Optional[Decimal]
    rate_per_km:     Decimal
    total_charge:    Decimal
    route_details:   Optional[Any] = None

    model_config = {"from_attributes": True}


class DarshanBookingDetail(BaseModel):
    id:               UUID
    temple_id:        UUID
    darshan_slot_id:  UUID
    darshan_type_id:  UUID
    darshan_date:     date
    darshan_time:     time
    num_persons:      int
    price_per_person: Decimal
    total_price:      Decimal
    devotee_details:  Any
    ticket_number:    Optional[str]

    model_config = {"from_attributes": True}


class PackageBookingDetail(BaseModel):
    id:             UUID
    package_id:     UUID
    start_date:     date
    end_date:       date
    num_adults:     int
    num_children:   int
    package_price:  Decimal
    addon_charges:  Decimal
    total_price:    Decimal
    customizations: Optional[Any]

    model_config = {"from_attributes": True}


class GuideBookingDetail(BaseModel):
    id:                 UUID
    guide_id:           UUID
    start_date:         date
    end_date:           date
    start_time:         Optional[time]
    end_time:           Optional[time]
    num_hours:          Optional[int]
    num_days:           Optional[int]
    rate:               Decimal
    total_charge:       Decimal
    meeting_point:      Optional[str]
    locations_to_cover: Optional[Any]

    model_config = {"from_attributes": True}


class PoojaBookingDetail(BaseModel):
    id:                   UUID
    pooja_service_id:     UUID
    pooja_date:           date
    pooja_time:           Optional[time]
    devotee_names:        Any
    gothram:              Optional[str]
    nakshatra:            Optional[str]
    special_instructions: Optional[str]
    price:                Decimal

    model_config = {"from_attributes": True}


class PrasadamOrderDetail(BaseModel):
    id:               UUID
    prasadam_item_id: UUID
    quantity:         int
    unit_price:       Decimal
    total_price:      Decimal
    delivery_status:  DeliveryStatus
    tracking_number:  Optional[str]

    model_config = {"from_attributes": True}


class TravelerDetail(BaseModel):
    id:              UUID
    name:            str
    age:             int
    gender:          Optional[Gender]
    id_proof_type:   Optional[str]
    is_primary:      bool

    model_config = {"from_attributes": True}


class AddonDetail(BaseModel):
    id:          UUID
    addon_type:  str
    addon_name:  str
    quantity:    int
    unit_price:  Decimal
    total_price: Decimal

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# BOOKING LIST SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class BookingListItem(BaseModel):
    """Single row in GET /, GET /upcoming, GET /past, GET /cancelled."""
    id:             UUID
    booking_number: str
    booking_type:   BookingType
    status:         BookingStatus
    payment_status: PaymentStatus
    total_amount:   Decimal
    paid_amount:    Decimal
    start_date:     Optional[date]
    end_date:       Optional[date]
    created_at:     datetime
    # extra fields for GET /cancelled
    cancellation_reason: Optional[str]      = None
    cancelled_at:        Optional[datetime] = None
    refund_amount:       Optional[Decimal]  = None
    refund_status:       Optional[str]      = None   # pending | processed | failed

    model_config = {"from_attributes": True}


class BookingListResponse(BaseModel):
    """Paginated wrapper used by all booking list endpoints."""
    items:       List[BookingListItem]
    total:       int
    page:        int
    per_page:    int
    total_pages: int


# ─────────────────────────────────────────────────────────────────────────────
# BOOKING DETAIL RESPONSE
# ─────────────────────────────────────────────────────────────────────────────

class BookingDetailResponse(BaseModel):
    """GET /bookings/{id}
    Excel: Full booking detail including items, payment, guide, driver, itinerary.
    """
    id:             UUID
    booking_number: str
    booking_type:   BookingType
    status:         BookingStatus
    payment_status: PaymentStatus
    booking_date:   date
    start_date:     Optional[date]
    end_date:       Optional[date]

    # financials
    subtotal:        Decimal
    discount_amount: Decimal
    tax_amount:      Decimal
    convenience_fee: Decimal
    total_amount:    Decimal
    paid_amount:     Decimal
    coupon_code:     Optional[str]

    # contact & requests
    special_requests:    Optional[str]
    contact_details:     Optional[Any]
    cancellation_reason: Optional[str]

    # timestamps
    cancelled_at: Optional[datetime]
    confirmed_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at:   datetime
    updated_at:   datetime

    # payment snapshot
    payment_info: Optional[PaymentInfoSchema] = None

    # sub-booking — only one populated based on booking_type
    hotel_booking:   Optional[HotelBookingDetail]        = None
    vehicle_booking: Optional[VehicleBookingDetail]      = None
    darshan_booking: Optional[DarshanBookingDetail]      = None
    package_booking: Optional[PackageBookingDetail]      = None
    guide_booking:   Optional[GuideBookingDetail]        = None
    pooja_booking:   Optional[PoojaBookingDetail]        = None
    prasadam_orders: Optional[List[PrasadamOrderDetail]] = None

    # travelers & addons
    travelers: Optional[List[TravelerDetail]] = None
    addons:    Optional[List[AddonDetail]]    = None

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# INVOICE RESPONSE  (GET /bookings/{id}/invoice)
# ─────────────────────────────────────────────────────────────────────────────

class InvoiceLineItem(BaseModel):
    description: str
    quantity:    int
    unit_price:  Decimal
    total:       Decimal


class InvoiceResponse(BaseModel):
    """GET /bookings/{id}/invoice
    Excel: Download invoice PDF with GST breakdown and payment proof.
    """
    invoice_number:  str
    booking_number:  str
    booking_type:    BookingType
    customer_name:   str
    customer_phone:  str
    customer_email:  Optional[str]
    invoice_date:    date
    line_items:      List[InvoiceLineItem]
    subtotal:        Decimal
    discount:        Decimal
    cgst:            Decimal   # 9%
    sgst:            Decimal   # 9%
    total_tax:       Decimal
    convenience_fee: Decimal
    total_amount:    Decimal
    paid_amount:     Decimal
    payment_method:  Optional[str]
    payment_proof:   Optional[str]   # Razorpay payment ID
    pdf_url:         Optional[str]   # S3 URL of generated invoice PDF


# ─────────────────────────────────────────────────────────────────────────────
# TICKET RESPONSE  (GET /bookings/{id}/ticket)
# ─────────────────────────────────────────────────────────────────────────────

class TicketResponse(BaseModel):
    """GET /bookings/{id}/ticket
    Excel: Download e-ticket with QR code for darshan or pooja.
    Booking Flow: step 32 → {ticket_url, qr_code} returned after payment confirmed.
    """
    ticket_number:  str
    booking_number: str
    booking_type:   BookingType   # darshan | pooja
    temple_name:    str
    darshan_type:   Optional[str]
    pooja_name:     Optional[str]
    visit_date:     date
    visit_time:     Optional[time]
    num_persons:    int
    devotee_names:  List[str]
    qr_code_url:    str            # S3 URL of QR code image
    pdf_url:        Optional[str]  # S3 URL of ticket PDF
    instructions:   Optional[str]  # dress code, items allowed, etc.


# ─────────────────────────────────────────────────────────────────────────────
# CANCEL & MODIFY SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class CancelBookingRequest(BaseModel):
    """PUT /bookings/{id}/cancel"""
    reason: str = Field(..., min_length=5, max_length=500)


class CancelBookingResponse(BaseModel):
    """SOW refund policy:
    > 48 hrs  → 100% refund
    24–48 hrs → 50%  refund
    < 24 hrs  → no   refund
    """
    booking_id:     UUID
    booking_number: str
    status:         BookingStatus
    refund_amount:  Decimal
    refund_percent: int = Field(..., description="100 | 50 | 0")
    refund_status:  str = Field(..., description="initiated | not_applicable")
    message:        str


class ModifyBookingRequest(BaseModel):
    """POST /bookings/{id}/modify
    Excel: Request modification — date or guest change requiring admin approval.
    """
    new_start_date:  Optional[date] = None
    new_end_date:    Optional[date] = None
    new_guest_count: Optional[int]  = Field(None, ge=1, le=50)
    reason:          str            = Field(..., min_length=5, max_length=500)


class ModifyBookingResponse(BaseModel):
    booking_id:     UUID
    booking_number: str
    status:         BookingStatus
    message:        str   # "Modification request submitted for admin approval"


# ─────────────────────────────────────────────────────────────────────────────
# TRACKING RESPONSE  (GET /bookings/{id}/tracking)
# Excel: Get live tracking data for active trip.
# Redis: driver_loc:{booking_id}  TTL 30s
# ─────────────────────────────────────────────────────────────────────────────

class BookingTrackingResponse(BaseModel):
    booking_id:       UUID
    booking_number:   str
    driver_name:      Optional[str]
    driver_phone:     Optional[str]
    vehicle_number:   Optional[str]
    current_lat:      Optional[Decimal]
    current_lng:      Optional[Decimal]
    current_location: Optional[str]
    eta_minutes:      Optional[int]
    status:           BookingStatus
    last_updated:     Optional[datetime]
