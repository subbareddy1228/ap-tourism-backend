"""
schemas/vehicle.py
Vehicle module schemas — fixed for Pydantic v2 (LEV146 pattern).
Changes:
  - @validator → @field_validator
  - .from_orm() → .model_validate()
  - root_validator removed
"""

from typing import Optional, List, Any, Dict
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

from src.models.vehicle import VehicleType, VehicleStatus, DriverStatus, VehicleDocumentType


# ─── Vehicle Type Info ────────────────────────────────────────

class VehicleTypeInfo(BaseModel):
    type:             str
    base_rate_per_km: float
    description:      str


# ─── Vehicle Document ─────────────────────────────────────────

class VehicleDocumentCreate(BaseModel):
    document_type: VehicleDocumentType
    expiry_date:   Optional[datetime] = None


class VehicleDocumentResponse(BaseModel):
    id:            UUID
    vehicle_id:    UUID
    document_type: VehicleDocumentType
    file_url:      str
    expiry_date:   Optional[datetime]
    is_verified:   bool
    created_at:    datetime

    model_config = {"from_attributes": True}


# ─── Driver ───────────────────────────────────────────────────

class DriverCreate(BaseModel):
    name:           str   = Field(..., min_length=2, max_length=200)
    phone:          str   = Field(..., pattern=r"^\+?[0-9]{10,15}$")
    license_number: str   = Field(..., min_length=5, max_length=50)
    license_expiry: datetime
    photo_url:      Optional[str] = None


class DriverUpdate(BaseModel):
    name:           Optional[str]      = Field(None, min_length=2, max_length=200)
    phone:          Optional[str]      = None
    license_number: Optional[str]      = None
    license_expiry: Optional[datetime] = None
    photo_url:      Optional[str]      = None


class DriverStatusUpdate(BaseModel):
    status: DriverStatus


class DriverResponse(BaseModel):
    id:             UUID
    partner_id:     UUID
    vehicle_id:     Optional[UUID]
    name:           str
    phone:          str
    license_number: str
    license_expiry: datetime
    photo_url:      Optional[str]
    status:         DriverStatus
    rating:         float
    total_trips:    int
    created_at:     datetime

    model_config = {"from_attributes": True}


# ─── Vehicle ──────────────────────────────────────────────────

class VehicleCreate(BaseModel):
    vehicle_type:        VehicleType
    make:                str   = Field(..., min_length=1, max_length=100)
    model:               str   = Field(..., min_length=1, max_length=100)
    year:                int   = Field(..., ge=2000, le=2030)
    registration_number: str   = Field(..., min_length=5, max_length=20)
    color:               Optional[str]          = None
    capacity:            int   = Field(..., ge=1, le=50)
    has_ac:              bool  = True
    has_wifi:            bool  = False
    has_gps:             bool  = False
    gps_device_id:       Optional[str]          = None
    features:            Optional[Dict[str, Any]] = {}
    current_city:        Optional[str]          = None
    available_cities:    Optional[List[str]]    = []
    price_per_km:        Optional[float]        = None
    min_fare:            Optional[float]        = 200.0

    @field_validator("year")
    @classmethod
    def validate_year(cls, v):
        if v < 2000 or v > 2030:
            raise ValueError("Vehicle year must be between 2000 and 2030")
        return v


class VehicleUpdate(BaseModel):
    make:             Optional[str]   = Field(None, max_length=100)
    model:            Optional[str]   = Field(None, max_length=100)
    year:             Optional[int]   = None
    color:            Optional[str]   = None
    capacity:         Optional[int]   = Field(None, ge=1, le=50)
    has_ac:           Optional[bool]  = None
    has_wifi:         Optional[bool]  = None
    has_gps:          Optional[bool]  = None
    gps_device_id:    Optional[str]   = None
    features:         Optional[Dict[str, Any]] = None
    current_city:     Optional[str]   = None
    available_cities: Optional[List[str]] = None


class VehicleStatusUpdate(BaseModel):
    status: VehicleStatus


class VehiclePricingUpdate(BaseModel):
    price_per_km: float = Field(..., gt=0)
    min_fare:     Optional[float] = Field(None, gt=0)


class VehicleAssignDriver(BaseModel):
    driver_id: UUID


class VehicleResponse(BaseModel):
    id:                  UUID
    partner_id:          UUID
    vehicle_type:        VehicleType
    make:                str
    model:               str
    year:                int
    registration_number: str
    color:               Optional[str]
    capacity:            int
    has_ac:              bool
    has_wifi:            bool
    has_gps:             bool
    features:            Optional[Dict[str, Any]]
    price_per_km:        float
    min_fare:            float
    current_city:        Optional[str]
    available_cities:    Optional[List[str]]
    status:              VehicleStatus
    images:              Optional[List[str]]
    rating:              float
    total_reviews:       int
    total_trips:         int
    created_at:          datetime
    updated_at:          Optional[datetime]

    model_config = {"from_attributes": True}


class VehicleDetailResponse(VehicleResponse):
    documents: Optional[List[VehicleDocumentResponse]] = []
    drivers:   Optional[List[DriverResponse]]          = []


# ─── Availability & Fare ──────────────────────────────────────

class AvailabilityRequest(BaseModel):
    pickup_date:     datetime
    pickup_address:  str
    drop_address:    str
    vehicle_type:    Optional[VehicleType] = None
    capacity_needed: Optional[int]         = None


class AvailabilityResponse(BaseModel):
    vehicle_id:            UUID
    is_available:          bool
    vehicle:               VehicleResponse
    estimated_distance_km: Optional[float]
    estimated_fare:        Optional[float]


class FareCalculationRequest(BaseModel):
    pickup_address: str
    drop_address:   str
    vehicle_type:   VehicleType
    vehicle_id:     Optional[UUID] = None


class FareCalculationResponse(BaseModel):
    vehicle_type:   str
    pickup_address: str
    drop_address:   str
    distance_km:    float
    base_fare:      float
    toll_estimate:  float
    total_fare:     float
    currency:       str = "INR"


# ─── Paginated ────────────────────────────────────────────────

class PaginatedVehicleResponse(BaseModel):
    data:  List[VehicleResponse]
    total: int
    page:  int
    pages: int
    limit: int


class PaginatedDriverResponse(BaseModel):
    data:  List[DriverResponse]
    total: int
    page:  int
    pages: int
    limit: int