"""
api/v1/endpoints/vehicles.py
Vehicle module — all endpoints using LEV146 patterns.

Public:
  GET  /vehicles/types              — Vehicle types with base rates
  GET  /vehicles/availability       — Check availability
  POST /vehicles/calculate-fare     — Calculate trip fare
  GET  /vehicles/                   — List available vehicles
  GET  /vehicles/{vehicle_id}       — Vehicle detail
  GET  /vehicles/{vehicle_id}/reviews — Vehicle reviews

Partner — Vehicles:
  POST   /vehicles/                              — Add vehicle
  PUT    /vehicles/{vehicle_id}                  — Update vehicle
  DELETE /vehicles/{vehicle_id}                  — Remove vehicle
  PUT    /vehicles/{vehicle_id}/status           — Toggle status
  PUT    /vehicles/{vehicle_id}/pricing          — Update pricing
  PUT    /vehicles/{vehicle_id}/assign-driver    — Assign driver
  POST   /vehicles/{vehicle_id}/images           — Upload image
  DELETE /vehicles/{vehicle_id}/images/{img_id}  — Delete image
  POST   /vehicles/{vehicle_id}/documents        — Upload document

Partner — Drivers:
  GET    /vehicles/drivers                       — List drivers
  POST   /vehicles/drivers                       — Add driver
  PUT    /vehicles/drivers/{driver_id}           — Update driver
  DELETE /vehicles/drivers/{driver_id}           — Remove driver
  PUT    /vehicles/drivers/{driver_id}/status    — Set driver status
"""

from typing import Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, Query, UploadFile, File, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.api.deps.auth import get_current_user, get_partner_user
from src.models.user import User
from src.models.vehicle import VehicleType, VehicleStatus, DriverStatus, VehicleDocumentType
from src.schemas.vehicle import (
    VehicleCreate, VehicleUpdate, VehicleStatusUpdate, VehiclePricingUpdate,
    VehicleAssignDriver, DriverCreate, DriverUpdate, DriverStatusUpdate,
    FareCalculationRequest, AvailabilityRequest,
    VehicleResponse, VehicleDetailResponse,
    DriverResponse,
    FareCalculationResponse, VehicleTypeInfo,
)
from src.common.responses import APIResponse
from src.services.vehicle_service import VehicleService

router = APIRouter(prefix="/vehicles", tags=["Vehicles"])


# ── Dependency ────────────────────────────────────────────────
async def get_vehicle_service(db: AsyncSession = Depends(get_db)) -> VehicleService:
    return VehicleService(db)


# ══════════════════════════════════════════════════════════════
# PUBLIC ENDPOINTS
# Static routes MUST come before /{vehicle_id}
# ══════════════════════════════════════════════════════════════

@router.get("/types", response_model=APIResponse, summary="Vehicle types with base rates")
async def get_vehicle_types(service: VehicleService = Depends(get_vehicle_service)):
    """All vehicle types with base rate per km and description."""
    data = await service.get_vehicle_types()
    return APIResponse.success(message="Vehicle types fetched", data=[t.model_dump() for t in data])


@router.get("/availability", response_model=APIResponse, summary="Check vehicle availability")
async def check_availability(
    pickup_date:      datetime            = Query(...),
    pickup_address:   str                 = Query(...),
    drop_address:     str                 = Query(...),
    vehicle_type:     Optional[VehicleType] = Query(None),
    capacity_needed:  Optional[int]       = Query(None),
    service: VehicleService = Depends(get_vehicle_service),
):
    """Check available vehicles for given date, route and capacity."""
    request = AvailabilityRequest(
        pickup_date=pickup_date, pickup_address=pickup_address,
        drop_address=drop_address, vehicle_type=vehicle_type,
        capacity_needed=capacity_needed,
    )
    results = await service.check_availability(request)
    return APIResponse.success(message=f"{len(results)} vehicles available", data=results)


@router.post("/calculate-fare", response_model=APIResponse, summary="Calculate trip fare")
async def calculate_fare(
    request: FareCalculationRequest,
    service: VehicleService = Depends(get_vehicle_service),
):
    """Calculate fare using OSRM distance matrix. No API key needed."""
    fare = await service.calculate_fare(request)
    return APIResponse.success(message="Fare calculated", data=fare)


@router.get("/drivers", response_model=APIResponse, summary="[Partner] List drivers")
async def list_drivers(
    page:  int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_partner_user),
    service: VehicleService = Depends(get_vehicle_service),
):
    """List all drivers registered by the current partner."""
    drivers, total, page, pages = await service.list_drivers(
        partner_id=current_user.id, page=page, limit=limit
    )
    return APIResponse.success(
        message=f"{total} drivers found",
        data={
            "data":  [VehicleService.driver_to_dict(d) for d in drivers],
            "total": total, "page": page, "pages": pages, "limit": limit,
        }
    )


@router.post("/drivers", response_model=APIResponse, status_code=201, summary="[Partner] Add driver")
async def create_driver(
    data: DriverCreate,
    current_user: User = Depends(get_partner_user),
    service: VehicleService = Depends(get_vehicle_service),
):
    """Register a new driver under the current partner."""
    driver = await service.create_driver(partner_id=current_user.id, data=data)
    return APIResponse.success(message="Driver registered successfully", data=VehicleService.driver_to_dict(driver))


@router.put("/drivers/{driver_id}", response_model=APIResponse, summary="[Partner] Update driver")
async def update_driver(
    driver_id: UUID,
    data: DriverUpdate,
    current_user: User = Depends(get_partner_user),
    service: VehicleService = Depends(get_vehicle_service),
):
    driver = await service.update_driver(partner_id=current_user.id, driver_id=driver_id, data=data)
    return APIResponse.success(message="Driver updated", data=VehicleService.driver_to_dict(driver))


@router.delete("/drivers/{driver_id}", response_model=APIResponse, summary="[Partner] Remove driver")
async def delete_driver(
    driver_id: UUID,
    current_user: User = Depends(get_partner_user),
    service: VehicleService = Depends(get_vehicle_service),
):
    result = await service.delete_driver(partner_id=current_user.id, driver_id=driver_id)
    return APIResponse.success(message=result["message"])


@router.put("/drivers/{driver_id}/status", response_model=APIResponse, summary="[Partner] Set driver status")
async def update_driver_status(
    driver_id: UUID,
    data: DriverStatusUpdate,
    current_user: User = Depends(get_partner_user),
    service: VehicleService = Depends(get_vehicle_service),
):
    driver = await service.update_driver_status(
        partner_id=current_user.id, driver_id=driver_id, status=data.status
    )
    return APIResponse.success(message="Driver status updated", data=VehicleService.driver_to_dict(driver))


@router.get("", response_model=APIResponse, summary="List available vehicles")
async def list_vehicles(
    vehicle_type: Optional[VehicleType] = Query(None),
    city: Optional[str] = Query(None),
    pickup_date: Optional[datetime] = Query(None),
    capacity: Optional[int] = Query(None),
    has_ac: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    service: VehicleService = Depends(get_vehicle_service),
):
    """Browse active vehicles with filters: type, city, date, capacity, AC."""
    vehicles, total, page, pages = await service.list_vehicles(
        vehicle_type=vehicle_type,
        city=city,
        pickup_date=pickup_date,
        capacity=capacity,
        has_ac=has_ac,
        page=page,
        limit=limit,
    )

    return APIResponse.success(
        message=f"{total} vehicles found",
        data={
            "data": [VehicleService.vehicle_to_dict(v) for v in vehicles],
            "total": total,
            "page": page,
            "pages": pages,
            "limit": limit,
        },
    )


# ══════════════════════════════════════════════════════════════
# VEHICLE DETAIL
# ══════════════════════════════════════════════════════════════

@router.get("/{vehicle_id}/reviews", response_model=APIResponse, summary="Vehicle reviews")
async def get_vehicle_reviews(
    vehicle_id: UUID,
    page:  int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    service: VehicleService = Depends(get_vehicle_service),
):
    reviews, total, page, pages = await service.get_vehicle_reviews(vehicle_id, page, limit)
    return APIResponse.success(
        message=f"{total} reviews",
        data={"data": reviews, "total": total, "page": page, "pages": pages, "limit": limit}
    )


@router.get("/{vehicle_id}", response_model=APIResponse, summary="Vehicle detail")
async def get_vehicle(
    vehicle_id: UUID,
    service: VehicleService = Depends(get_vehicle_service),
):
    """Full vehicle detail including documents and assigned driver."""
    vehicle = await service.get_vehicle(vehicle_id)
    return APIResponse.success(message="Vehicle fetched", data=VehicleService.vehicle_to_dict(vehicle))


# ══════════════════════════════════════════════════════════════
# PARTNER — VEHICLE CRUD
# ══════════════════════════════════════════════════════════════

@router.post("", response_model=APIResponse, status_code=201, summary="[Partner] Add vehicle")
async def create_vehicle(
    data: VehicleCreate,
    current_user: User = Depends(get_partner_user),
    service: VehicleService = Depends(get_vehicle_service),
):
    """Register a new vehicle. Price defaults to base rate for vehicle type."""
    vehicle = await service.create_vehicle(partner_id=current_user.id, data=data)
    return APIResponse.success(message="Vehicle registered successfully", data=VehicleService.vehicle_to_dict(vehicle))


@router.put("/{vehicle_id}", response_model=APIResponse, summary="[Partner] Update vehicle")
async def update_vehicle(
    vehicle_id: UUID,
    data: VehicleUpdate,
    current_user: User = Depends(get_partner_user),
    service: VehicleService = Depends(get_vehicle_service),
):
    vehicle = await service.update_vehicle(partner_id=current_user.id, vehicle_id=vehicle_id, data=data)
    return APIResponse.success(message="Vehicle updated", data=VehicleService.vehicle_to_dict(vehicle))


@router.delete("/{vehicle_id}", response_model=APIResponse, summary="[Partner] Remove vehicle")
async def delete_vehicle(
    vehicle_id: UUID,
    current_user: User = Depends(get_partner_user),
    service: VehicleService = Depends(get_vehicle_service),
):
    """Soft delete — vehicle is deactivated not permanently deleted."""
    await service.delete_vehicle(partner_id=current_user.id, vehicle_id=vehicle_id)
    return APIResponse.success(message="Vehicle removed successfully")


@router.put("/{vehicle_id}/status", response_model=APIResponse, summary="[Partner] Toggle vehicle status")
async def update_vehicle_status(
    vehicle_id: UUID,
    data: VehicleStatusUpdate,
    current_user: User = Depends(get_partner_user),
    service: VehicleService = Depends(get_vehicle_service),
):
    vehicle = await service.update_vehicle_status(
        partner_id=current_user.id, vehicle_id=vehicle_id, status=data.status
    )
    return APIResponse.success(message="Status updated", data=VehicleService.vehicle_to_dict(vehicle))


@router.put("/{vehicle_id}/pricing", response_model=APIResponse, summary="[Partner] Update vehicle pricing")
async def update_vehicle_pricing(
    vehicle_id: UUID,
    data: VehiclePricingUpdate,
    current_user: User = Depends(get_partner_user),
    service: VehicleService = Depends(get_vehicle_service),
):
    vehicle = await service.update_vehicle_pricing(
        partner_id=current_user.id, vehicle_id=vehicle_id, data=data
    )
    return APIResponse.success(message="Pricing updated", data=VehicleService.vehicle_to_dict(vehicle))


@router.put("/{vehicle_id}/assign-driver", response_model=APIResponse, summary="[Partner] Assign driver")
async def assign_driver_to_vehicle(
    vehicle_id: UUID,
    data: VehicleAssignDriver,
    current_user: User = Depends(get_partner_user),
    service: VehicleService = Depends(get_vehicle_service),
):
    vehicle = await service.assign_driver(
        partner_id=current_user.id, vehicle_id=vehicle_id, driver_id=data.driver_id
    )
    return APIResponse.success(message="Driver assigned", data=VehicleService.vehicle_to_dict(vehicle))


@router.post("/{vehicle_id}/images", response_model=APIResponse, status_code=201, summary="[Partner] Upload vehicle image")
async def upload_vehicle_image(
    vehicle_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_partner_user),
    service: VehicleService = Depends(get_vehicle_service),
):
    """Upload vehicle image. Max 5MB. JPG/PNG/WEBP only."""
    vehicle = await service.upload_vehicle_image(
        partner_id=current_user.id, vehicle_id=vehicle_id, file=file
    )
    return APIResponse.success(message="Image uploaded", data=VehicleService.vehicle_to_dict(vehicle))


@router.delete("/{vehicle_id}/images/{img_id:path}", response_model=APIResponse, summary="[Partner] Delete vehicle image")
async def delete_vehicle_image(
    vehicle_id: UUID,
    img_id: str,
    current_user: User = Depends(get_partner_user),
    service: VehicleService = Depends(get_vehicle_service),
):
    await service.delete_vehicle_image(
        partner_id=current_user.id, vehicle_id=vehicle_id, img_id=img_id
    )
    return APIResponse.success(message="Image deleted")


@router.post("/{vehicle_id}/documents", response_model=APIResponse, status_code=201, summary="[Partner] Upload vehicle document")
async def upload_vehicle_document(
    vehicle_id:    UUID,
    file:          UploadFile = File(...),
    document_type: VehicleDocumentType = Form(...),
    expiry_date:   Optional[datetime]   = Form(None),
    current_user: User = Depends(get_partner_user),
    service: VehicleService = Depends(get_vehicle_service),
):
    """Upload KYC document: RC, Insurance, Fitness, Permit, PUC."""
    doc = await service.upload_vehicle_document(
        partner_id=current_user.id, vehicle_id=vehicle_id,
        file=file, document_type=document_type, expiry_date=expiry_date,
    )
    return APIResponse.success(message="Document uploaded successfully", data=doc)
