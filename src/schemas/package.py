from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from src.models.package import PackageType


# ─────────────────────────────────────────
# NESTED SCHEMAS
# ─────────────────────────────────────────

class ItineraryDay(BaseModel):
    day: int
    title: str
    description: Optional[str] = None
    meals: Optional[str] = None           # e.g. "Breakfast, Dinner"
    accommodation: Optional[str] = None   # e.g. "Hotel Araku"


class PricingRule(BaseModel):
    label: str                            # e.g. "Group of 5-10"
    min_people: int
    max_people: int
    price_per_person: float


class PackageImage(BaseModel):
    url: str
    caption: Optional[str] = None
    is_hero: bool = False


# ─────────────────────────────────────────
# BASE SCHEMA
# ─────────────────────────────────────────

class PackageBase(BaseModel):
    name: str = Field(..., example="Araku Valley 3 Days Tour")
    slug: str = Field(..., example="araku-valley-3-days")
    destination_id: str = Field(..., example="f3a1b2c4-9d8e-4f2a-b1c3-a2b3c4d5e6f7")
    type: PackageType

    duration_days: int = Field(..., ge=1, example=3)
    duration_nights: int = Field(..., ge=0, example=2)

    price: float = Field(..., ge=0, example=5999.0)

    group_size: Optional[int] = None

    itinerary: List[ItineraryDay] = []
    inclusions: List[str] = []
    exclusions: List[str] = []
    pricing_rules: Optional[List[PricingRule]] = None
    departure_dates: List[str] = []
    images: List[PackageImage] = []


# ─────────────────────────────────────────
# CREATE SCHEMA
# ─────────────────────────────────────────

class PackageCreate(PackageBase):
    is_featured: Optional[bool] = False
    is_active: Optional[bool] = True


# ─────────────────────────────────────────
# UPDATE SCHEMA
# ─────────────────────────────────────────

class PackageUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    destination_id: Optional[str] = None
    type: Optional[PackageType] = None

    duration_days: Optional[int] = None
    duration_nights: Optional[int] = None

    price: Optional[float] = None
    group_size: Optional[int] = None

    itinerary: Optional[List[ItineraryDay]] = None
    inclusions: Optional[List[str]] = None
    exclusions: Optional[List[str]] = None
    pricing_rules: Optional[List[PricingRule]] = None
    departure_dates: Optional[List[str]] = None
    images: Optional[List[PackageImage]] = None

    is_featured: Optional[bool] = None
    is_active: Optional[bool] = None


# ─────────────────────────────────────────
# RESPONSE SCHEMA
# ─────────────────────────────────────────

class PackageResponse(PackageBase):
    id: str
    rating: float
    reviews_count: int
    total_bookings: int
    is_featured: bool
    is_active: bool

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True