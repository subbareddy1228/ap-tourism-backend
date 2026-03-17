"""
Module 6 - Vehicle Service
Business logic for Vehicle APIs
Integrates with ORS for distance/fare calculation and AWS S3 for images
"""

import uuid
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.vehicle_repo import VehicleRepository, DriverRepository, VehicleDocumentRepository
from src.models.vehicle import VehicleType, VehicleStatus, DriverStatus, VEHICLE_BASE_RATES
from src.schemas.vehicle import (
    VehicleCreate, VehicleUpdate, VehicleStatusUpdate, VehiclePricingUpdate,
    VehicleAssignDriver, DriverCreate, DriverUpdate, DriverStatusUpdate,
    FareCalculationRequest, AvailabilityRequest,
    VehicleTypeInfo,
)
from src.integrations.google_maps import GoogleMapsClient
from src.integrations.aws_s3 import S3Client


VEHICLE_TYPE_DESCRIPTIONS = {
    VehicleType.SEDAN: "Comfortable 4-seater car, ideal for city travel",
    VehicleType.SUV: "Spacious 6-7 seater, suitable for families",
    VehicleType.TEMPO_TRAVELLER: "12-16 seater mini-bus for group travel",
    VehicleType.BUS: "Large 30+ seater for pilgrim groups",
    VehicleType.AUTO: "3-wheeler for short city distances",
    VehicleType.BIKE: "2-wheeler for solo quick travel",
}


class VehicleService:
    """Service layer for Vehicle business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.vehicle_repo = VehicleRepository(db)
        self.driver_repo = DriverRepository(db)
        self.doc_repo = VehicleDocumentRepository(db)
        self.maps_client = GoogleMapsClient()
        self.s3_client = S3Client()

    # ─── Public Endpoints ─────────────────────────────────────────────────────

    def get_vehicle_types(self) -> List[VehicleTypeInfo]:
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
        vehicle = await self.vehicle_repo.get_by_id(vehicle_id)
        if not vehicle:
            raise HTTPException(status_code=404, detail="Vehicle not found")
        return vehicle

    async def get_vehicle_reviews(self, vehicle_id: UUID, page: int = 1, limit: int = 20):
        vehicle = await self.vehicle_repo.get_by_id(vehicle_id)
        if not vehicle:
            raise HTTPException(status_code=404, detail="Vehicle not found")
        reviews, total = await self.vehicle_repo.get_reviews(vehicle_id, page, limit)
        pages = (total + limit - 1) // limit
        return reviews, total, page, pages

    async def calculate_fare(self, request: FareCalculationRequest) -> Dict[str, Any]:
        """Calculate trip fare using ORS Distance Matrix."""
        try:
            distance_result = self.maps_client.get_distance(
                origin=request.pickup_address,
                destination=request.drop_address,
            )
            distance_km = distance_result.get("distance_km", 0)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[FARE] DISTANCE ERROR: {type(e).__name__}: {e}", flush=True)
            distance_km = 0.0

        vehicle_id = request.vehicle_id
        if vehicle_id:
            vehicle = await self.vehicle_repo.get_by_id(vehicle_id)
            rate = vehicle.price_per_km if vehicle else VEHICLE_BASE_RATES[request.vehicle_type]
            min_fare = vehicle.min_fare if vehicle else 200.0
        else:
            rate = VEHICLE_BASE_RATES[request.vehicle_type]
            min_fare = 200.0

        base_fare = max(distance_km * rate, min_fare)
        toll_estimate = round(distance_km * 0.5, 2)
        total_fare = round(base_fare + toll_estimate, 2)

        return {
            "vehicle_type": request.vehicle_type.value,
            "pickup_address": request.pickup_address,
            "drop_address": request.drop_address,
            "distance_km": round(distance_km, 2),
            "base_fare": round(base_fare, 2),
            "toll_estimate": toll_estimate,
            "total_fare": total_fare,
            "currency": "INR",
        }

    async def check_availability(self, request: AvailabilityRequest) -> List[Dict[str, Any]]:
        vehicles, total = await self.vehicle_repo.list_vehicles(
            vehicle_type=request.vehicle_type,
            capacity=request.capacity_needed,
            pickup_date=request.pickup_date,
            page=1,
            limit=50,
        )
        results = []
        for vehicle in vehicles:
            results.append({
                "vehicle_id": vehicle.id,
                "is_available": True,
                "vehicle": vehicle,
                "estimated_distance_km": None,
                "estimated_fare": None,
            })
        return results

    # ─── Partner Endpoints ────────────────────────────────────────────────────

    async def create_vehicle(self, partner_id: UUID, data: VehicleCreate):
        existing = await self.vehicle_repo.get_by_registration(data.registration_number)
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Vehicle with registration '{data.registration_number}' already exists",
            )
        vehicle_data = data.dict()
        if not vehicle_data.get("price_per_km"):
            vehicle_data["price_per_km"] = VEHICLE_BASE_RATES[data.vehicle_type]
        return await self.vehicle_repo.create(partner_id=partner_id, data=vehicle_data)

    async def update_vehicle(self, partner_id: UUID, vehicle_id: UUID, data: VehicleUpdate):
        vehicle = await self._get_partner_vehicle(partner_id, vehicle_id)
        update_data = {k: v for k, v in data.dict().items() if v is not None}
        return await self.vehicle_repo.update(vehicle, update_data)

    async def delete_vehicle(self, partner_id: UUID, vehicle_id: UUID):
        vehicle = await self._get_partner_vehicle(partner_id, vehicle_id)
        return await self.vehicle_repo.soft_delete(vehicle)

    async def update_vehicle_status(self, partner_id: UUID, vehicle_id: UUID, status: VehicleStatus):
        vehicle = await self._get_partner_vehicle(partner_id, vehicle_id)
        return await self.vehicle_repo.update_status(vehicle, status)

    async def upload_vehicle_image(self, partner_id: UUID, vehicle_id: UUID, file: UploadFile):
        vehicle = await self._get_partner_vehicle(partner_id, vehicle_id)
        s3_key = f"vehicles/{vehicle_id}/images/{uuid.uuid4()}_{file.filename}"
        image_url = self.s3_client.upload_file(file.file, s3_key, file.content_type)
        return await self.vehicle_repo.add_image(vehicle, image_url)

    async def delete_vehicle_image(self, partner_id: UUID, vehicle_id: UUID, img_id: str):
        vehicle = await self._get_partner_vehicle(partner_id, vehicle_id)
        try:
            self.s3_client.delete_file(img_id)
        except Exception:
            pass
        return await self.vehicle_repo.remove_image(vehicle, img_id)

    async def update_vehicle_pricing(self, partner_id: UUID, vehicle_id: UUID, data: VehiclePricingUpdate):
        vehicle = await self._get_partner_vehicle(partner_id, vehicle_id)
        return await self.vehicle_repo.update_pricing(vehicle, data.price_per_km, data.min_fare)

    async def upload_vehicle_document(self, partner_id: UUID, vehicle_id: UUID, file: UploadFile, document_type: str, expiry_date=None):
        vehicle = await self._get_partner_vehicle(partner_id, vehicle_id)
        s3_key = f"vehicles/{vehicle_id}/documents/{uuid.uuid4()}_{file.filename}"
        doc_url = self.s3_client.upload_file(file.file, s3_key, file.content_type)
        return await self.doc_repo.create(
            vehicle_id=vehicle_id,
            data={"document_type": document_type, "file_url": doc_url, "expiry_date": expiry_date},
        )

    async def assign_driver(self, partner_id: UUID, vehicle_id: UUID, driver_id: UUID):
        vehicle = await self._get_partner_vehicle(partner_id, vehicle_id)
        driver = await self.driver_repo.get_by_id(driver_id)
        if not driver:
            raise HTTPException(status_code=404, detail="Driver not found")
        if str(driver.partner_id) != str(partner_id):
            raise HTTPException(status_code=403, detail="Driver does not belong to this partner")
        return await self.vehicle_repo.assign_driver(vehicle, driver_id)

    # ─── Driver Endpoints ─────────────────────────────────────────────────────

    async def list_drivers(self, partner_id: UUID, page: int = 1, limit: int = 20):
        drivers, total = await self.driver_repo.list_by_partner(partner_id, page, limit)
        pages = (total + limit - 1) // limit
        return drivers, total, page, pages

    async def create_driver(self, partner_id: UUID, data: DriverCreate):
        existing = await self.driver_repo.get_by_license(data.license_number)
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Driver with license '{data.license_number}' already registered",
            )
        return await self.driver_repo.create(partner_id=partner_id, data=data.dict())

    async def update_driver(self, partner_id: UUID, driver_id: UUID, data: DriverUpdate):
        driver = await self._get_partner_driver(partner_id, driver_id)
        update_data = {k: v for k, v in data.dict().items() if v is not None}
        return await self.driver_repo.update(driver, update_data)

    async def delete_driver(self, partner_id: UUID, driver_id: UUID):
        driver = await self._get_partner_driver(partner_id, driver_id)
        await self.driver_repo.delete(driver)
        return {"success": True, "message": "Driver removed successfully"}

    async def update_driver_status(self, partner_id: UUID, driver_id: UUID, status: DriverStatus):
        driver = await self._get_partner_driver(partner_id, driver_id)
        return await self.driver_repo.update_status(driver, status)

    # ─── Helpers ──────────────────────────────────────────────────────────────

    async def _get_partner_vehicle(self, partner_id: UUID, vehicle_id: UUID):
        vehicle = await self.vehicle_repo.get_by_id(vehicle_id)
        if not vehicle:
            raise HTTPException(status_code=404, detail="Vehicle not found")
        if str(vehicle.partner_id) != str(partner_id):
            raise HTTPException(status_code=403, detail="You do not have permission to manage this vehicle")
        return vehicle

    async def _get_partner_driver(self, partner_id: UUID, driver_id: UUID):
        driver = await self.driver_repo.get_by_id(driver_id)
        if not driver:
            raise HTTPException(status_code=404, detail="Driver not found")
        if str(driver.partner_id) != str(partner_id):
            raise HTTPException(status_code=403, detail="You do not have permission to manage this driver")
        return driver
