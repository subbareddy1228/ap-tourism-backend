"""
Module 6 - Vehicle Schemas
Pydantic models: CreateSchema, UpdateSchema, ResponseSchema per resource
"""

from typing import Optional, List, Any, Dict
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, validator, root_validator

from src.models.vehicle import VehicleType, VehicleStatus, DriverStatus, VehicleDocumentType


# ─── Vehicle Type Info ────────────────────────────────────────────────────────

class VehicleTypeInfo(BaseModel):
    type: str
    base_rate_per_km: float
    description: str


# ─── Vehicle Image ────────────────────────────────────────────────────────────

class VehicleImageResponse(BaseModel):
    img_id: str
    url: str
    uploaded_at: Optional[datetime]


# ─── Vehicle Document ─────────────────────────────────────────────────────────

class VehicleDocumentCreate(BaseModel):
    document_type: VehicleDocumentType
    expiry_date: Optional[datetime]


class VehicleDocumentResponse(BaseModel):
    id: UUID
    vehicle_id: UUID
    document_type: VehicleDocumentType
    file_url: str
    expiry_date: Optional[datetime]
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Driver ───────────────────────────────────────────────────────────────────

class DriverCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    phone: str = Field(..., pattern=r"^\+?[0-9]{10,15}$")
    license_number: str = Field(..., min_length=5, max_length=50)
    license_expiry: datetime
    photo_url: Optional[str]


class DriverUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    phone: Optional[str] = Field(None, pattern=r"^\+?[0-9]{10,15}$")
    license_number: Optional[str]
    license_expiry: Optional[datetime]
    photo_url: Optional[str]


class DriverStatusUpdate(BaseModel):
    status: DriverStatus


class DriverResponse(BaseModel):
    id: UUID
    partner_id: UUID
    vehicle_id: Optional[UUID]
    name: str
    phone: str
    license_number: str
    license_expiry: datetime
    photo_url: Optional[str]
    status: DriverStatus
    rating: float
    total_trips: int
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Vehicle ──────────────────────────────────────────────────────────────────

class VehicleCreate(BaseModel):
    vehicle_type: VehicleType
    make: str = Field(..., min_length=1, max_length=100)
    model: str = Field(..., min_length=1, max_length=100)
    year: int = Field(..., ge=2000, le=2030)
    registration_number: str = Field(..., min_length=5, max_length=20)
    color: Optional[str]
    capacity: int = Field(..., ge=1, le=50)
    has_ac: bool = True
    has_wifi: bool = False
    has_gps: bool = False
    gps_device_id: Optional[str]
    features: Optional[Dict[str, Any]] = {}
    current_city: Optional[str]
    available_cities: Optional[List[str]] = []
    price_per_km: Optional[float] = None   # defaults to base rate for type
    min_fare: Optional[float] = 200.0

    @validator("year")
    def validate_year(cls, v):
        if v < 2000 or v > 2030:
            raise ValueError("Vehicle year must be between 2000 and 2030")
        return v


class VehicleUpdate(BaseModel):
    make: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    year: Optional[int]
    color: Optional[str]
    capacity: Optional[int] = Field(None, ge=1, le=50)
    has_ac: Optional[bool]
    has_wifi: Optional[bool]
    has_gps: Optional[bool]
    gps_device_id: Optional[str]
    features: Optional[Dict[str, Any]]
    current_city: Optional[str]
    available_cities: Optional[List[str]]


class VehicleStatusUpdate(BaseModel):
    status: VehicleStatus


class VehiclePricingUpdate(BaseModel):
    price_per_km: float = Field(..., gt=0)
    min_fare: Optional[float] = Field(None, gt=0)


class VehicleAssignDriver(BaseModel):
    driver_id: UUID


class VehicleResponse(BaseModel):
    id: UUID
    partner_id: UUID
    vehicle_type: VehicleType
    make: str
    model: str
    year: int
    registration_number: str
    color: Optional[str]
    capacity: int
    has_ac: bool
    has_wifi: bool
    has_gps: bool
    features: Optional[Dict[str, Any]]
    price_per_km: float
    min_fare: float
    current_city: Optional[str]
    available_cities: Optional[List[str]]
    status: VehicleStatus
    images: Optional[List[str]]
    rating: float
    total_reviews: int
    total_trips: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class VehicleDetailResponse(VehicleResponse):
    documents: Optional[List[VehicleDocumentResponse]] = []
    drivers: Optional[List[DriverResponse]] = []


# ─── Availability & Fare Calculation ─────────────────────────────────────────

class AvailabilityRequest(BaseModel):
    pickup_date: datetime
    pickup_address: str
    drop_address: str
    vehicle_type: Optional[VehicleType]
    capacity_needed: Optional[int]


class AvailabilityResponse(BaseModel):
    vehicle_id: UUID
    is_available: bool
    vehicle: VehicleResponse
    estimated_distance_km: Optional[float]
    estimated_fare: Optional[float]


class FareCalculationRequest(BaseModel):
    pickup_address: str
    drop_address: str
    vehicle_type: VehicleType
    vehicle_id: Optional[UUID]


class FareCalculationResponse(BaseModel):
    vehicle_type: str
    pickup_address: str
    drop_address: str
    distance_km: float
    base_fare: float
    toll_estimate: float
    total_fare: float
    currency: str = "INR"


# ─── Paginated Responses ──────────────────────────────────────────────────────

class PaginatedVehicleResponse(BaseModel):
    data: List[VehicleResponse]
    total: int
    page: int
    pages: int
    limit: int


class PaginatedDriverResponse(BaseModel):
    data: List[DriverResponse]
    total: int
    page: int
    pages: int
    limit: int


class PaginatedReviewResponse(BaseModel):
    data: List[Dict]
    total: int
    page: int
    pages: int
    limit: int
