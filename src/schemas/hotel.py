from typing import Optional, List
from pydantic import BaseModel, field_validator
from src.common.enums import RoomType


# ─── Hotel Schemas ────────────────────────────────────────────

class HotelCreateSchema(BaseModel):
    name:                str
    description:         Optional[str]   = None
    address_line1:       str
    address_line2:       Optional[str]   = None
    city:                str
    district:            str
    state:               str             = "Andhra Pradesh"
    pincode:             str
    latitude:            Optional[float] = None
    longitude:           Optional[float] = None
    star_rating:         int             = 3
    check_in_time:       str             = "12:00"
    check_out_time:      str             = "11:00"
    cancellation_policy: Optional[str]   = None
    amenities:           List[str]       = []
    phone:               Optional[str]   = None
    email:               Optional[str]   = None
    website:             Optional[str]   = None

    @field_validator("star_rating")
    @classmethod
    def validate_star_rating(cls, v):
        if not 1 <= v <= 5:
            raise ValueError("Star rating must be between 1 and 5")
        return v

    @field_validator("pincode")
    @classmethod
    def validate_pincode(cls, v):
        if not v.isdigit() or len(v) != 6:
            raise ValueError("Pincode must be 6 digits")
        return v


class HotelUpdateSchema(BaseModel):
    name:                Optional[str]   = None
    description:         Optional[str]   = None
    address_line1:       Optional[str]   = None
    address_line2:       Optional[str]   = None
    city:                Optional[str]   = None
    district:            Optional[str]   = None
    state:               Optional[str]   = None
    pincode:             Optional[str]   = None
    latitude:            Optional[float] = None
    longitude:           Optional[float] = None
    star_rating:         Optional[int]   = None
    check_in_time:       Optional[str]   = None
    check_out_time:      Optional[str]   = None
    cancellation_policy: Optional[str]   = None
    phone:               Optional[str]   = None
    email:               Optional[str]   = None
    website:             Optional[str]   = None


# ─── Room Schemas ─────────────────────────────────────────────

class RoomCreateSchema(BaseModel):
    name:            str
    description:     Optional[str] = None
    room_type:       RoomType      = RoomType.STANDARD
    capacity:        int           = 2
    price_per_night: float
    total_rooms:     int           = 1
    amenities:       List[str]     = []

    @field_validator("price_per_night")
    @classmethod
    def validate_price(cls, v):
        if v <= 0:
            raise ValueError("Price must be greater than 0")
        return v

    @field_validator("capacity", "total_rooms")
    @classmethod
    def validate_positive(cls, v):
        if v <= 0:
            raise ValueError("Value must be greater than 0")
        return v


class RoomUpdateSchema(BaseModel):
    name:            Optional[str]       = None
    description:     Optional[str]       = None
    room_type:       Optional[RoomType]  = None
    capacity:        Optional[int]       = None
    price_per_night: Optional[float]     = None
    total_rooms:     Optional[int]       = None
    amenities:       Optional[List[str]] = None


class RoomPricingSchema(BaseModel):
    price_per_night: float

    @field_validator("price_per_night")
    @classmethod
    def validate_price(cls, v):
        if v <= 0:
            raise ValueError("Price must be greater than 0")
        return v


class RoomAvailabilitySchema(BaseModel):
    is_active: bool


class RoomBlockSchema(BaseModel):
    block_dates: List[str]
    reason:      Optional[str] = None


# ─── Amenity / Image Schemas ──────────────────────────────────

class AmenityAddSchema(BaseModel):
    amenity: str
