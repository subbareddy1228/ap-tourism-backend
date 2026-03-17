"""
Module 6 - Vehicle API Endpoints
Base URL: /api/v1/vehicles
"""

from typing import Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession as AsyncSession

from src.api.deps.database import get_db
from src.services.vehicle_service import VehicleService
from src.models.vehicle import VehicleType, VehicleStatus, DriverStatus, VehicleDocumentType
from src.schemas.vehicle import (
    VehicleCreate, VehicleUpdate, VehicleStatusUpdate, VehiclePricingUpdate,
    VehicleAssignDriver, DriverCreate, DriverUpdate, DriverStatusUpdate,
    FareCalculationRequest, AvailabilityRequest,
    VehicleResponse, VehicleDetailResponse,
    DriverResponse,
    FareCalculationResponse, VehicleTypeInfo,
)
from src.common.responses import success_response

router = APIRouter(prefix="/vehicles", tags=["Vehicle APIs"])

DUMMY_PARTNER = "00000000-0000-0000-0000-000000000000"


# ─── Dependency ───────────────────────────────────────────────────────────────

def get_vehicle_service(db: AsyncSession = Depends(get_db)) -> VehicleService:
    return VehicleService(db)


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/", summary="List available vehicles")
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
    vehicles, total, page, pages = await service.list_vehicles(
        vehicle_type=vehicle_type, city=city, pickup_date=pickup_date,
        capacity=capacity, has_ac=has_ac, page=page, limit=limit,
    )
    return success_response(data={
        "data": [VehicleResponse.from_orm(v) for v in vehicles],
        "total": total, "page": page, "pages": pages, "limit": limit,
    })


@router.get("/types", summary="Vehicle types with base rates")
async def get_vehicle_types(service: VehicleService = Depends(get_vehicle_service)):
    return success_response(data=service.get_vehicle_types())


@router.get("/availability", summary="Check vehicle availability")
async def check_availability(
    pickup_date: datetime = Query(...),
    pickup_address: str = Query(...),
    drop_address: str = Query(...),
    vehicle_type: Optional[VehicleType] = Query(None),
    capacity_needed: Optional[int] = Query(None),
    service: VehicleService = Depends(get_vehicle_service),
):
    request = AvailabilityRequest(
        pickup_date=pickup_date, pickup_address=pickup_address,
        drop_address=drop_address, vehicle_type=vehicle_type,
        capacity_needed=capacity_needed,
    )
    results = await service.check_availability(request)
    return success_response(data=results)


@router.post("/calculate-fare", summary="Calculate trip fare")
async def calculate_fare(
    request: FareCalculationRequest,
    service: VehicleService = Depends(get_vehicle_service),
):
    fare = await service.calculate_fare(request)
    return success_response(data=fare)


# ─── Driver routes BEFORE /{vehicle_id} ──────────────────────────────────────

@router.get("/drivers", summary="List drivers (Partner)")
async def list_drivers(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    service: VehicleService = Depends(get_vehicle_service),
):
    drivers, total, page, pages = await service.list_drivers(
        partner_id=DUMMY_PARTNER, page=page, limit=limit
    )
    return success_response(data={
        "data": [DriverResponse.from_orm(d) for d in drivers],
        "total": total, "page": page, "pages": pages, "limit": limit,
    })


@router.post("/drivers", status_code=201, summary="Add driver (Partner)")
async def create_driver(
    data: DriverCreate,
    service: VehicleService = Depends(get_vehicle_service),
):
    driver = await service.create_driver(partner_id=DUMMY_PARTNER, data=data)
    return success_response(data=DriverResponse.from_orm(driver), message="Driver registered successfully")


@router.put("/drivers/{driver_id}", summary="Update driver (Partner)")
async def update_driver(
    driver_id: UUID, data: DriverUpdate,
    service: VehicleService = Depends(get_vehicle_service),
):
    driver = await service.update_driver(partner_id=DUMMY_PARTNER, driver_id=driver_id, data=data)
    return success_response(data=DriverResponse.from_orm(driver), message="Driver updated")


@router.delete("/drivers/{driver_id}", summary="Remove driver (Partner)")
async def delete_driver(
    driver_id: UUID,
    service: VehicleService = Depends(get_vehicle_service),
):
    result = await service.delete_driver(partner_id=DUMMY_PARTNER, driver_id=driver_id)
    return success_response(**result)


@router.put("/drivers/{driver_id}/status", summary="Set driver status (Partner)")
async def update_driver_status(
    driver_id: UUID, data: DriverStatusUpdate,
    service: VehicleService = Depends(get_vehicle_service),
):
    driver = await service.update_driver_status(partner_id=DUMMY_PARTNER, driver_id=driver_id, status=data.status)
    return success_response(data=DriverResponse.from_orm(driver), message="Driver status updated")


# ─── /{vehicle_id} routes ─────────────────────────────────────────────────────

@router.get("/{vehicle_id}", summary="Vehicle detail")
async def get_vehicle(
    vehicle_id: UUID,
    service: VehicleService = Depends(get_vehicle_service),
):
    vehicle = await service.get_vehicle(vehicle_id)
    return success_response(data=VehicleDetailResponse.from_orm(vehicle))


@router.get("/{vehicle_id}/reviews", summary="Vehicle reviews")
async def get_vehicle_reviews(
    vehicle_id: UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    service: VehicleService = Depends(get_vehicle_service),
):
    reviews, total, page, pages = await service.get_vehicle_reviews(vehicle_id, page, limit)
    return success_response(data={
        "data": reviews, "total": total, "page": page, "pages": pages, "limit": limit,
    })


# ═══════════════════════════════════════════════════════════════════════════════
# PARTNER — VEHICLE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/", status_code=201, summary="Add new vehicle (Partner)")
async def create_vehicle(
    data: VehicleCreate,
    service: VehicleService = Depends(get_vehicle_service),
):
    vehicle = await service.create_vehicle(partner_id=DUMMY_PARTNER, data=data)
    return success_response(data=VehicleResponse.from_orm(vehicle), message="Vehicle registered successfully")


@router.put("/{vehicle_id}", summary="Update vehicle (Partner)")
async def update_vehicle(
    vehicle_id: UUID, data: VehicleUpdate,
    service: VehicleService = Depends(get_vehicle_service),
):
    vehicle = await service.update_vehicle(partner_id=DUMMY_PARTNER, vehicle_id=vehicle_id, data=data)
    return success_response(data=VehicleResponse.from_orm(vehicle), message="Vehicle updated")


@router.delete("/{vehicle_id}", summary="Remove vehicle (Partner)")
async def delete_vehicle(
    vehicle_id: UUID,
    service: VehicleService = Depends(get_vehicle_service),
):
    await service.delete_vehicle(partner_id=DUMMY_PARTNER, vehicle_id=vehicle_id)
    return success_response(message="Vehicle removed successfully")


@router.put("/{vehicle_id}/status", summary="Toggle vehicle status (Partner)")
async def update_vehicle_status(
    vehicle_id: UUID, data: VehicleStatusUpdate,
    service: VehicleService = Depends(get_vehicle_service),
):
    vehicle = await service.update_vehicle_status(partner_id=DUMMY_PARTNER, vehicle_id=vehicle_id, status=data.status)
    return success_response(data=VehicleResponse.from_orm(vehicle), message="Status updated")


@router.post("/{vehicle_id}/images", status_code=201, summary="Upload vehicle image (Partner)")
async def upload_vehicle_image(
    vehicle_id: UUID, file: UploadFile = File(...),
    service: VehicleService = Depends(get_vehicle_service),
):
    vehicle = await service.upload_vehicle_image(partner_id=DUMMY_PARTNER, vehicle_id=vehicle_id, file=file)
    return success_response(data=VehicleResponse.from_orm(vehicle), message="Image uploaded")


@router.delete("/{vehicle_id}/images/{img_id:path}", summary="Delete vehicle image (Partner)")
async def delete_vehicle_image(
    vehicle_id: UUID, img_id: str,
    service: VehicleService = Depends(get_vehicle_service),
):
    await service.delete_vehicle_image(partner_id=DUMMY_PARTNER, vehicle_id=vehicle_id, img_id=img_id)
    return success_response(message="Image deleted")


@router.put("/{vehicle_id}/pricing", summary="Update vehicle pricing (Partner)")
async def update_vehicle_pricing(
    vehicle_id: UUID, data: VehiclePricingUpdate,
    service: VehicleService = Depends(get_vehicle_service),
):
    vehicle = await service.update_vehicle_pricing(partner_id=DUMMY_PARTNER, vehicle_id=vehicle_id, data=data)
    return success_response(data=VehicleResponse.from_orm(vehicle), message="Pricing updated")


@router.post("/{vehicle_id}/documents", status_code=201, summary="Upload vehicle document (Partner)")
async def upload_vehicle_document(
    vehicle_id: UUID,
    file: UploadFile = File(...),
    document_type: VehicleDocumentType = Form(...),
    expiry_date: Optional[datetime] = Form(None),
    service: VehicleService = Depends(get_vehicle_service),
):
    doc = await service.upload_vehicle_document(
        partner_id=DUMMY_PARTNER, vehicle_id=vehicle_id,
        file=file, document_type=document_type, expiry_date=expiry_date,
    )
    return success_response(data=doc, message="Document uploaded successfully")


@router.put("/{vehicle_id}/assign-driver", summary="Assign driver to vehicle (Partner)")
async def assign_driver_to_vehicle(
    vehicle_id: UUID, data: VehicleAssignDriver,
    service: VehicleService = Depends(get_vehicle_service),
):
    vehicle = await service.assign_driver(
        partner_id=DUMMY_PARTNER, vehicle_id=vehicle_id, driver_id=data.driver_id,
    )
    return success_response(data=VehicleResponse.from_orm(vehicle), message="Driver assigned")
