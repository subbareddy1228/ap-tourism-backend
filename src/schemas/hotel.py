"""
schemas/hotel.py
Pydantic schemas for all Hotel module endpoints (M5).

Public endpoints  — traveler browsing, room search, availability check
Partner endpoints — hotel CRUD, room management, image upload, inventory
"""

from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, field_validator


VALID_HOTEL_TYPES  = ["HOTEL", "RESORT", "HOMESTAY", "GUESTHOUSE", "DHARAMSHALA"]
VALID_ROOM_TYPES   = ["STANDARD", "DELUXE", "SUITE", "FAMILY", "DORMITORY"]
VALID_BED_TYPES    = ["SINGLE", "DOUBLE", "TWIN", "KING", "QUEEN"]
VALID_IMG_CATS     = ["EXTERIOR", "INTERIOR", "ROOM", "RESTAURANT", "POOL", "OTHER"]
VALID_MEAL_OPTIONS = ["ROOM_ONLY", "BED_BREAKFAST", "HALF_BOARD", "FULL_BOARD"]


# ══════════════════ HOTEL CREATE / UPDATE ══════════════════

class HotelCreateRequest(BaseModel):
    name:                 str
    description:          Optional[str] = None
    star_rating:          int = 3
    hotel_type:           str = "HOTEL"
    address:              str
    city:                 str
    state:                str
    pincode:              Optional[str] = None
    latitude:             Optional[float] = None
    longitude:            Optional[float] = None
    distance_from_temple: Optional[float] = None
    contact_phone:        Optional[str] = None
    contact_email:        Optional[str] = None
    website:              Optional[str] = None
    check_in_time:        str = "12:00"
    check_out_time:       str = "11:00"
    cancellation_policy:  Optional[str] = None
    pet_policy:           str = "NOT_ALLOWED"
    meal_options:         Optional[List[str]] = None

    @field_validator("star_rating")
    @classmethod
    def star_range(cls, v):
        if v not in range(1, 6):
            raise ValueError("star_rating must be between 1 and 5")
        return v

    @field_validator("hotel_type")
    @classmethod
    def type_valid(cls, v):
        if v.upper() not in VALID_HOTEL_TYPES:
            raise ValueError(f"hotel_type must be one of: {', '.join(VALID_HOTEL_TYPES)}")
        return v.upper()


class HotelUpdateRequest(BaseModel):
    name:                 Optional[str] = None
    description:          Optional[str] = None
    star_rating:          Optional[int] = None
    hotel_type:           Optional[str] = None
    address:              Optional[str] = None
    city:                 Optional[str] = None
    state:                Optional[str] = None
    pincode:              Optional[str] = None
    latitude:             Optional[float] = None
    longitude:            Optional[float] = None
    distance_from_temple: Optional[float] = None
    contact_phone:        Optional[str] = None
    contact_email:        Optional[str] = None
    website:              Optional[str] = None
    check_in_time:        Optional[str] = None
    check_out_time:       Optional[str] = None
    cancellation_policy:  Optional[str] = None
    pet_policy:           Optional[str] = None
    meal_options:         Optional[List[str]] = None

    @field_validator("star_rating")
    @classmethod
    def star_range(cls, v):
        if v is not None and v not in range(1, 6):
            raise ValueError("star_rating must be between 1 and 5")
        return v


# ══════════════════ HOTEL RESPONSE ══════════════════

class HotelRoomResponse(BaseModel):
    id:               str
    room_type:        str
    name:             Optional[str]
    description:      Optional[str]
    max_occupancy:    int
    total_rooms:      int
    price_per_night:  float
    weekend_price:    Optional[float]
    extra_bed_price:  float
    bed_type:         Optional[str]
    has_ac:           bool
    has_wifi:         bool
    has_tv:           bool
    has_geyser:       bool
    is_smoking:       bool
    amenities:        Optional[List[str]]
    is_active:        bool
    created_at:       datetime

    class Config:
        from_attributes = True

    @field_validator("id", mode="before")
    @classmethod
    def str_uuid(cls, v):
        return str(v)

    @field_validator("price_per_night", "extra_bed_price", mode="before")
    @classmethod
    def decimal_to_float(cls, v):
        return float(v) if v is not None else 0.0

    @field_validator("weekend_price", mode="before")
    @classmethod
    def optional_decimal(cls, v):
        return float(v) if v is not None else None


class HotelImageResponse(BaseModel):
    id:            str
    image_url:     str
    caption:       Optional[str]
    category:      str
    is_primary:    bool
    display_order: int

    class Config:
        from_attributes = True

    @field_validator("id", mode="before")
    @classmethod
    def str_uuid(cls, v):
        return str(v)


class HotelAmenityResponse(BaseModel):
    id:       str
    name:     str
    category: Optional[str]
    icon:     Optional[str]
    is_paid:  bool

    class Config:
        from_attributes = True

    @field_validator("id", mode="before")
    @classmethod
    def str_uuid(cls, v):
        return str(v)


class HotelResponse(BaseModel):
    id:                   str
    partner_id:           str
    name:                 str
    description:          Optional[str]
    star_rating:          int
    hotel_type:           str
    address:              str
    city:                 str
    state:                str
    pincode:              Optional[str]
    latitude:             Optional[float]
    longitude:            Optional[float]
    distance_from_temple: Optional[float]
    contact_phone:        Optional[str]
    contact_email:        Optional[str]
    website:              Optional[str]
    check_in_time:        str
    check_out_time:       str
    cancellation_policy:  Optional[str]
    pet_policy:           str
    meal_options:         Optional[List[str]]
    is_active:            bool
    is_featured:          bool
    status:               str
    base_price:           Optional[float]
    rating:               Optional[float]
    total_reviews:        int
    rooms:                List[HotelRoomResponse] = []
    images:               List[HotelImageResponse] = []
    amenities:            List[HotelAmenityResponse] = []
    created_at:           datetime

    class Config:
        from_attributes = True

    @field_validator("id", "partner_id", mode="before")
    @classmethod
    def str_uuid(cls, v):
        return str(v)

    @field_validator("base_price", mode="before")
    @classmethod
    def optional_decimal(cls, v):
        return float(v) if v is not None else None


class HotelListResponse(BaseModel):
    """Lightweight response for listing — no nested rooms/amenities."""
    id:                   str
    name:                 str
    star_rating:          int
    hotel_type:           str
    city:                 str
    state:                str
    distance_from_temple: Optional[float]
    base_price:           Optional[float]
    rating:               Optional[float]
    total_reviews:        int
    is_featured:          bool
    primary_image:        Optional[str] = None   # primary image URL injected by service

    class Config:
        from_attributes = True

    @field_validator("id", mode="before")
    @classmethod
    def str_uuid(cls, v):
        return str(v)

    @field_validator("base_price", mode="before")
    @classmethod
    def optional_decimal(cls, v):
        return float(v) if v is not None else None


# ══════════════════ ROOM CREATE / UPDATE ══════════════════

class RoomCreateRequest(BaseModel):
    room_type:        str
    name:             Optional[str] = None
    description:      Optional[str] = None
    max_occupancy:    int = 2
    total_rooms:      int = 1
    price_per_night:  float
    weekend_price:    Optional[float] = None
    extra_bed_price:  float = 0.0
    bed_type:         Optional[str] = None
    has_ac:           bool = True
    has_wifi:         bool = True
    has_tv:           bool = True
    has_geyser:       bool = True
    is_smoking:       bool = False
    amenities:        Optional[List[str]] = None

    @field_validator("room_type")
    @classmethod
    def type_valid(cls, v):
        if v.upper() not in VALID_ROOM_TYPES:
            raise ValueError(f"room_type must be one of: {', '.join(VALID_ROOM_TYPES)}")
        return v.upper()

    @field_validator("bed_type")
    @classmethod
    def bed_valid(cls, v):
        if v and v.upper() not in VALID_BED_TYPES:
            raise ValueError(f"bed_type must be one of: {', '.join(VALID_BED_TYPES)}")
        return v.upper() if v else v

    @field_validator("price_per_night")
    @classmethod
    def price_positive(cls, v):
        if v <= 0:
            raise ValueError("price_per_night must be greater than 0")
        return v

    @field_validator("max_occupancy", "total_rooms")
    @classmethod
    def positive_int(cls, v):
        if v < 1:
            raise ValueError("Value must be at least 1")
        return v


class RoomUpdateRequest(BaseModel):
    name:             Optional[str] = None
    description:      Optional[str] = None
    max_occupancy:    Optional[int] = None
    total_rooms:      Optional[int] = None
    price_per_night:  Optional[float] = None
    weekend_price:    Optional[float] = None
    extra_bed_price:  Optional[float] = None
    bed_type:         Optional[str] = None
    has_ac:           Optional[bool] = None
    has_wifi:         Optional[bool] = None
    has_tv:           Optional[bool] = None
    has_geyser:       Optional[bool] = None
    is_smoking:       Optional[bool] = None
    amenities:        Optional[List[str]] = None
    is_active:        Optional[bool] = None


# ══════════════════ AMENITY ══════════════════

class AmenityCreateRequest(BaseModel):
    name:     str
    category: Optional[str] = None
    icon:     Optional[str] = None
    is_paid:  bool = False


# ══════════════════ AVAILABILITY ══════════════════

class AvailabilityRequest(BaseModel):
    check_in:    date
    check_out:   date
    guests:      int = 1
    room_type:   Optional[str] = None

    @field_validator("check_out")
    @classmethod
    def checkout_after_checkin(cls, v, info):
        if "check_in" in info.data and v <= info.data["check_in"]:
            raise ValueError("check_out must be after check_in")
        return v

    @field_validator("guests")
    @classmethod
    def guests_positive(cls, v):
        if v < 1:
            raise ValueError("guests must be at least 1")
        return v


class AvailabilityResponse(BaseModel):
    hotel_id:        str
    check_in:        date
    check_out:       date
    nights:          int
    available_rooms: List[dict]  # list of {room_type, available_count, price_per_night, total_price}