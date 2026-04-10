"""
services/vehicle_service.py
Vehicle module — fixed for LEV146 integration.
Changes:
  - Added vehicle_to_dict() and driver_to_dict() helpers
  - UPLOAD_DIR uses local fallback if not in config
  - No .from_orm() usage
  - [MAPS] Replaced GoogleMapsClient with maps_client (Ola Maps)
"""

import uuid
import os
import aiofiles
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.vehicle_repo import VehicleRepository, DriverRepository, VehicleDocumentRepository
from src.models.vehicle import VehicleType, VehicleStatus, DriverStatus, VEHICLE_BASE_RATES, Vehicle, Driver
from src.schemas.vehicle import (
    VehicleCreate, VehicleUpdate, VehicleStatusUpdate, VehiclePricingUpdate,
    VehicleAssignDriver, DriverCreate, DriverUpdate, DriverStatusUpdate,
    FareCalculationRequest, AvailabilityRequest,
    VehicleTypeInfo,
)
# [MAPS] replaced: from src.integrations.google_maps import GoogleMapsClient
from src.integrations import maps_client
from src.core.exceptions import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
)

VEHICLE_TYPE_DESCRIPTIONS = {
    VehicleType.SEDAN:           "Comfortable 4-seater car, ideal for city travel",
    VehicleType.SUV:             "Spacious 6-7 seater, suitable for families",
    VehicleType.TEMPO_TRAVELLER: "12-16 seater mini-bus for group travel",
    VehicleType.BUS:             "Large 30+ seater for pilgrim groups",
    VehicleType.AUTO:            "3-wheeler for short city distances",
    VehicleType.BIKE:            "2-wheeler for solo quick travel",
}

class VehicleService:

    def __init__(self, db: Optional[AsyncSession] = None):

        self.db = db

        if db:
            self.vehicle_repo = VehicleRepository(db)
            self.driver_repo = DriverRepository(db)
            self.doc_repo = VehicleDocumentRepository(db)
        else:
            self.vehicle_repo = None
            self.driver_repo = None
            self.doc_repo = None

        # [MAPS] removed: self.maps_client = GoogleMapsClient()
        # maps_client is now a module-level set of functions, no instance needed

    # ── Dict Helpers (replaces .from_orm()) ───────────────────

    @staticmethod
    def vehicle_to_dict(vehicle: Vehicle) -> dict:
        return {
            "id":                  str(vehicle.id),
            "partner_id":         str(vehicle.partner_id),
            "vehicle_type":       vehicle.vehicle_type.value if vehicle.vehicle_type else None,
            "make":               vehicle.make,
            "model":              vehicle.model,
            "year":               vehicle.year,
            "registration_number": vehicle.registration_number,
            "color":              vehicle.color,
            "capacity":           vehicle.capacity,
            "has_ac":             vehicle.has_ac,
            "has_wifi":           vehicle.has_wifi,
            "has_gps":            vehicle.has_gps,
            "features":           vehicle.features or {},
            "price_per_km":       vehicle.price_per_km,
            "min_fare":           vehicle.min_fare,
            "current_city":       vehicle.current_city,
            "available_cities":   vehicle.available_cities or [],
            "status":             vehicle.status.value if vehicle.status else None,
            "images":             vehicle.images or [],
            "rating":             vehicle.rating,
            "total_reviews":      vehicle.total_reviews,
            "total_trips":        vehicle.total_trips,
            "created_at":         vehicle.created_at,
            "updated_at":         vehicle.updated_at,
        }

    @staticmethod
    def driver_to_dict(driver: Driver) -> dict:
        return {
            "id":             str(driver.id),
            "partner_id":     str(driver.partner_id),
            "vehicle_id":     str(driver.vehicle_id) if driver.vehicle_id else None,
            "name":           driver.name,
            "phone":          driver.phone,
            "license_number": driver.license_number,
            "license_expiry": driver.license_expiry,
            "photo_url":      driver.photo_url,
            "status":         driver.status.value if driver.status else None,
            "rating":         driver.rating,
            "total_trips":    driver.total_trips,
            "created_at":     driver.created_at,
        }

    # ── Public Endpoints ──────────────────────────────────────

    async def get_vehicle_types(self) -> List[VehicleTypeInfo]:
        return [
            VehicleTypeInfo(
                type=vtype.value,
                base_rate_per_km=VEHICLE_BASE_RATES[vtype],
                description=VEHICLE_TYPE_DESCRIPTIONS.get(vtype, ""),
            )
            for vtype in VehicleType
        ]

    async def list_vehicles(
    self,
    vehicle_type: Optional[VehicleType] = None,
    city: Optional[str] = None,
    pickup_date=None,
    capacity: Optional[int] = None,
    has_ac: Optional[bool] = None,
    page: int = 1,
    limit: int = 20,
):

    # If repository not available (pytest)
        if not self.vehicle_repo:
            return [], 0, page, 0

        vehicles, total = await self.vehicle_repo.list_vehicles(
        vehicle_type=vehicle_type,
        city=city,
        pickup_date=pickup_date,
        capacity=capacity,
        has_ac=has_ac,
        page=page,
        limit=limit,
    )

        pages = (total + limit - 1) // limit

        return vehicles, total, page, pages

    async def get_vehicle(self, vehicle_id: UUID):

        if not self.vehicle_repo:
            raise NotFoundException("Vehicle not found")

        vehicle = await self.vehicle_repo.get_by_id(vehicle_id)

        if not vehicle:
            raise NotFoundException("Vehicle not found")

        return vehicle

    async def get_vehicle_reviews(self, vehicle_id: UUID, page: int = 1, limit: int = 20):
        vehicle = await self.vehicle_repo.get_by_id(vehicle_id)
        if not vehicle:
            raise NotFoundException("Vehicle not found")
        reviews, total = await self.vehicle_repo.get_reviews(vehicle_id, page, limit)
        pages = (total + limit - 1) // limit
        return reviews, total, page, pages

    async def calculate_fare(self, request: FareCalculationRequest) -> Dict[str, Any]:
        """
        Calculate trip fare using Ola Maps distance_matrix.
        [MAPS] Replaced: self.maps_client.get_distance() (Nominatim + OSRM)
               With    : maps_client.distance_matrix()   (Ola Maps)
        Raises HTTPException 503 if maps service is down (no silent zero fallback).
        """
        try:
            result = await maps_client.distance_matrix(
                origin=request.pickup_address,
                destination=request.drop_address,
            )
            distance_km = result["distance_km"]
        except ValueError as e:
            # Address not found — return 400 to the caller
            raise BadRequestException(str(e))
        except RuntimeError as e:
            # Ola Maps API is down — return 503
            from src.core.exceptions import ServiceUnavailableException
            raise ServiceUnavailableException(f"Maps service unavailable: {e}")

        if request.vehicle_id:
            vehicle = await self.vehicle_repo.get_by_id(request.vehicle_id)
            rate     = vehicle.price_per_km if vehicle else VEHICLE_BASE_RATES[request.vehicle_type]
            min_fare = vehicle.min_fare     if vehicle else 200.0
        else:
            rate     = VEHICLE_BASE_RATES[request.vehicle_type]
            min_fare = 200.0

        base_fare     = max(distance_km * rate, min_fare)
        toll_estimate = round(distance_km * 0.5, 2)
        total_fare    = round(base_fare + toll_estimate, 2)

        return {
            "vehicle_type":   request.vehicle_type.value,
            "pickup_address": request.pickup_address,
            "drop_address":   request.drop_address,
            "distance_km":    round(distance_km, 2),
            "base_fare":      round(base_fare, 2),
            "toll_estimate":  toll_estimate,
            "total_fare":     total_fare,
            "currency":       "INR",
        }

    async def check_availability(self, request: AvailabilityRequest) -> List[Dict[str, Any]]:
        if not self.vehicle_repo:
            return []

        vehicles, total = await self.vehicle_repo.list_vehicles(
            vehicle_type=request.vehicle_type,
            capacity=request.capacity_needed,
            pickup_date=request.pickup_date,
            page=1,
            limit=50,
        )

        return [
            {
                "vehicle_id": str(v.id),
                "is_available": True,
                "vehicle": self.vehicle_to_dict(v),
            }
            for v in vehicles
        ]

    # ── Partner — Vehicle CRUD ────────────────────────────────

    async def create_vehicle(self, partner_id: UUID, data: VehicleCreate):
        existing = await self.vehicle_repo.get_by_registration(data.registration_number)
        if existing:
            raise ConflictException(f"Vehicle with registration '{data.registration_number}' already exists")
        vehicle_data = data.model_dump()
        if not vehicle_data.get("price_per_km"):
            vehicle_data["price_per_km"] = VEHICLE_BASE_RATES[data.vehicle_type]
        return await self.vehicle_repo.create(partner_id=partner_id, data=vehicle_data)

    async def update_vehicle(self, partner_id: UUID, vehicle_id: UUID, data: VehicleUpdate):
        vehicle     = await self._get_partner_vehicle(partner_id, vehicle_id)
        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        return await self.vehicle_repo.update(vehicle, update_data)

    async def delete_vehicle(self, partner_id: UUID, vehicle_id: UUID):
        vehicle = await self._get_partner_vehicle(partner_id, vehicle_id)
        return await self.vehicle_repo.soft_delete(vehicle)

    async def update_vehicle_status(self, partner_id: UUID, vehicle_id: UUID, status: VehicleStatus):
        vehicle = await self._get_partner_vehicle(partner_id, vehicle_id)
        return await self.vehicle_repo.update_status(vehicle, status)

    async def upload_vehicle_image(self, partner_id: UUID, vehicle_id: UUID, file: UploadFile):
        vehicle = await self._get_partner_vehicle(partner_id, vehicle_id)
        allowed = ["image/jpeg", "image/png", "image/jpg", "image/webp"]
        if file.content_type not in allowed:
            raise BadRequestException("Only JPG, PNG and WEBP images allowed")
        contents = await file.read()
        if len(contents) > 5 * 1024 * 1024:
            raise BadRequestException("Image size must be less than 5MB")

        upload_dir = "uploads/vehicles"
        os.makedirs(upload_dir, exist_ok=True)
        file_name  = f"{uuid.uuid4()}_{file.filename}"
        file_path  = os.path.join(upload_dir, file_name)
        image_url  = f"/uploads/vehicles/{file_name}"

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(contents)

        return await self.vehicle_repo.add_image(vehicle, image_url)

    async def delete_vehicle_image(self, partner_id: UUID, vehicle_id: UUID, img_id: str):
        vehicle = await self._get_partner_vehicle(partner_id, vehicle_id)
        return await self.vehicle_repo.remove_image(vehicle, img_id)

    async def update_vehicle_pricing(self, partner_id: UUID, vehicle_id: UUID, data: VehiclePricingUpdate):
        vehicle = await self._get_partner_vehicle(partner_id, vehicle_id)
        return await self.vehicle_repo.update_pricing(vehicle, data.price_per_km, data.min_fare)

    async def upload_vehicle_document(self, partner_id: UUID, vehicle_id: UUID, file: UploadFile, document_type: str, expiry_date=None):
        vehicle   = await self._get_partner_vehicle(partner_id, vehicle_id)
        file_url  = f"https://ap-tourism-media.s3.ap-south-1.amazonaws.com/vehicles/{vehicle_id}/docs/{uuid.uuid4()}_{file.filename}"
        return await self.doc_repo.create(
            vehicle_id=vehicle_id,
            data={"document_type": document_type, "file_url": file_url, "expiry_date": expiry_date},
        )

    async def assign_driver(self, partner_id: UUID, vehicle_id: UUID, driver_id: UUID):
        vehicle = await self._get_partner_vehicle(partner_id, vehicle_id)
        driver  = await self.driver_repo.get_by_id(driver_id)
        if not driver:
            raise NotFoundException("Driver not found")
        if str(driver.partner_id) != str(partner_id):
            raise ForbiddenException("Driver does not belong to this partner")
        return await self.vehicle_repo.assign_driver(vehicle, driver_id)

    # ── Driver Endpoints ──────────────────────────────────────

    async def list_drivers(self, partner_id: UUID, page: int = 1, limit: int = 20):
        drivers, total = await self.driver_repo.list_by_partner(partner_id, page, limit)
        pages = (total + limit - 1) // limit
        return drivers, total, page, pages

    async def create_driver(self, partner_id: UUID, data: DriverCreate):
        existing = await self.driver_repo.get_by_license(data.license_number)
        if existing:
            raise ConflictException(f"Driver with license '{data.license_number}' already registered")
        return await self.driver_repo.create(partner_id=partner_id, data=data.model_dump())

    async def update_driver(self, partner_id: UUID, driver_id: UUID, data: DriverUpdate):
        driver      = await self._get_partner_driver(partner_id, driver_id)
        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        return await self.driver_repo.update(driver, update_data)

    async def delete_driver(self, partner_id: UUID, driver_id: UUID):
        driver = await self._get_partner_driver(partner_id, driver_id)
        await self.driver_repo.delete(driver)
        return {"success": True, "message": "Driver removed successfully"}

    async def update_driver_status(self, partner_id: UUID, driver_id: UUID, status: DriverStatus):
        driver = await self._get_partner_driver(partner_id, driver_id)
        return await self.driver_repo.update_status(driver, status)

    # ── Helpers ───────────────────────────────────────────────

    async def _get_partner_vehicle(self, partner_id: UUID, vehicle_id: UUID):
        vehicle = await self.vehicle_repo.get_by_id(vehicle_id)
        if not vehicle:
            raise NotFoundException("Vehicle not found")
        if str(vehicle.partner_id) != str(partner_id):
            raise ForbiddenException("You do not have permission to manage this vehicle")
        return vehicle

    async def _get_partner_driver(self, partner_id: UUID, driver_id: UUID):
        driver = await self.driver_repo.get_by_id(driver_id)
        if not driver:
            raise NotFoundException("Driver not found")
        if str(driver.partner_id) != str(partner_id):
            raise ForbiddenException("You do not have permission to manage this driver")
        return driver

async def admin_list_vehicles(db: AsyncSession, page: int = 1, per_page: int = 20, status: Optional[str] = None):
    svc = VehicleService(db)
    vehicles, total = await svc.vehicle_repo.list_vehicles(
        vehicle_type=None,
        city=None,
        pickup_date=None,
        capacity=None,
        has_ac=None,
        page=page,
        limit=per_page,
    )
    pages = (total + per_page - 1) // per_page
    return {
        "items": [VehicleService.vehicle_to_dict(v) for v in vehicles],
        "total": total,
        "page": page,
        "pages": pages,
    }
