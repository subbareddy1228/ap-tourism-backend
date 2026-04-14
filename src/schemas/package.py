from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID


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


# This schema fixes your import error
class ItineraryDayCreate(ItineraryDay):
    pass


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
    name: str = Field(..., example="Vizag Explorer")
    slug: str = Field(..., example="vizag-explorer")
    destination_id: UUID = Field(..., example="00000000-0000-0000-0000-000000000001")
    type: PackageType

    duration_days: int = Field(..., ge=1, example=3)
    duration_nights: int = Field(..., ge=0, example=2)

    price: float = Field(..., ge=0, example=5999.0)

    group_size: Optional[int] = None

    # safer defaults
    itinerary: List[ItineraryDay] = Field(default_factory=list)
    inclusions: List[str] = Field(default_factory=list)
    exclusions: List[str] = Field(default_factory=list)

    pricing_rules: Optional[List[PricingRule]] = None
    departure_dates: List[str] = Field(default_factory=list)
    images: List[PackageImage] = Field(default_factory=list)


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
    id: UUID
    rating: float
    reviews_count: int
    total_bookings: int
    is_featured: bool
    is_active: bool

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        
# ─────────────────────────────────────────
# REQUEST SCHEMAS
# ─────────────────────────────────────────

class CalculatePriceRequest(BaseModel):
    package_id: UUID
    num_people: int = Field(..., ge=1, example=4)
    departure_date: Optional[str] = None

class CustomPackageRequest(BaseModel):
    destination_id: UUID
    duration_days: int = Field(..., ge=1, example=3)
    num_people: int = Field(..., ge=1, example=2)
    preferences: Optional[List[str]] = Field(default_factory=list)
    budget_per_person: Optional[float] = None
    departure_date: Optional[str] = None
    special_requests: Optional[str] = None        