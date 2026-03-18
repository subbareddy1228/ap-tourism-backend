"""
Module 6 - Vehicle Repository
Data access layer for Vehicle, Driver, VehicleDocument models
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, update
from sqlalchemy.orm import selectinload

from src.models.vehicle import Vehicle, Driver, VehicleDocument, VehicleReview, VehicleStatus, VehicleType


class VehicleRepository:
    """Repository for Vehicle CRUD and query operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ─── Create ───────────────────────────────────────────────────────────────

    async def create(self, partner_id: UUID, data: Dict[str, Any]) -> Vehicle:
        vehicle = Vehicle(partner_id=partner_id, **data)
        self.db.add(vehicle)
        await self.db.commit()
        await self.db.refresh(vehicle)
        return vehicle

    # ─── Read ─────────────────────────────────────────────────────────────────

    async def get_by_id(self, vehicle_id: UUID) -> Optional[Vehicle]:
        result = await self.db.execute(select(Vehicle).options(selectinload(Vehicle.documents),selectinload(Vehicle.drivers))
                                       .filter(Vehicle.id == vehicle_id, Vehicle.deleted_at.is_(None))
                                       )
        return result.scalars().first()

    async def get_by_registration(self, reg_number: str) -> Optional[Vehicle]:
        result = await self.db.execute(
            select(Vehicle).filter(Vehicle.registration_number == reg_number)
        )
        return result.scalars().first()

    async def list_vehicles(
        self,
        vehicle_type: Optional[VehicleType] = None,
        city: Optional[str] = None,
        pickup_date=None,
        capacity: Optional[int] = None,
        has_ac: Optional[bool] = None,
        status: VehicleStatus = VehicleStatus.ACTIVE,
        page: int = 1,
        limit: int = 20,
    ):
        query = select(Vehicle).filter(
            Vehicle.deleted_at.is_(None),
            Vehicle.status == status,
        )
        if vehicle_type:
            query = query.filter(Vehicle.vehicle_type == vehicle_type)
        if city:
            query = query.filter(
                or_(
                    Vehicle.current_city.ilike(f"%{city}%"),
                    Vehicle.available_cities.contains([city]),
                )
            )
        if capacity:
            query = query.filter(Vehicle.capacity >= capacity)
        if has_ac is not None:
            query = query.filter(Vehicle.has_ac == has_ac)

        count_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar()

        result = await self.db.execute(query.offset((page - 1) * limit).limit(limit))
        vehicles = result.scalars().all()
        return vehicles, total

    async def list_by_partner(self, partner_id: UUID, page: int = 1, limit: int = 20):
        query = select(Vehicle).filter(
            Vehicle.partner_id == partner_id,
            Vehicle.deleted_at.is_(None),
        )
        count_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar()

        result = await self.db.execute(query.offset((page - 1) * limit).limit(limit))
        vehicles = result.scalars().all()
        return vehicles, total

    # ─── Update ───────────────────────────────────────────────────────────────

    async def update(self, vehicle: Vehicle, data: Dict[str, Any]) -> Vehicle:
        for key, value in data.items():
            if value is not None:
                setattr(vehicle, key, value)
        vehicle.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(vehicle)
        return vehicle

    async def update_status(self, vehicle: Vehicle, status: VehicleStatus) -> Vehicle:
        vehicle.status = status
        vehicle.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(vehicle)
        return vehicle

    async def update_pricing(self, vehicle: Vehicle, price_per_km: float, min_fare: Optional[float] = None) -> Vehicle:
        vehicle.price_per_km = price_per_km
        if min_fare is not None:
            vehicle.min_fare = min_fare
        vehicle.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(vehicle)
        return vehicle

    async def assign_driver(self, vehicle: Vehicle, driver_id: UUID) -> Vehicle:
        await self.db.execute(
            update(Driver).where(Driver.vehicle_id == vehicle.id).values(vehicle_id=None)
        )
        driver_result = await self.db.execute(select(Driver).filter(Driver.id == driver_id))
        driver = driver_result.scalars().first()
        if driver:
            driver.vehicle_id = vehicle.id
        await self.db.commit()
        await self.db.refresh(vehicle)
        return vehicle

    # ─── Images ───────────────────────────────────────────────────────────────

    async def add_image(self, vehicle: Vehicle, image_url: str) -> Vehicle:
        images = vehicle.images or []
        images.append(image_url)
        vehicle.images = images
        vehicle.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(vehicle)
        return vehicle

    async def remove_image(self, vehicle: Vehicle, img_id: str) -> Vehicle:
        images = [img for img in (vehicle.images or []) if img != img_id]
        vehicle.images = images
        vehicle.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(vehicle)
        return vehicle

    # ─── Soft Delete ──────────────────────────────────────────────────────────

    async def soft_delete(self, vehicle: Vehicle) -> Vehicle:
        vehicle.deleted_at = datetime.utcnow()
        vehicle.status = VehicleStatus.INACTIVE
        await self.db.commit()
        return vehicle

    # ─── Reviews ──────────────────────────────────────────────────────────────

    async def get_reviews(self, vehicle_id: UUID, page: int = 1, limit: int = 20):
        query = select(VehicleReview).filter(VehicleReview.vehicle_id == vehicle_id)

        count_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar()

        result = await self.db.execute(query.offset((page - 1) * limit).limit(limit))
        reviews = result.scalars().all()
        return reviews, total

    async def update_rating(self, vehicle_id: UUID):
        avg_result = await self.db.execute(
            select(func.avg(VehicleReview.rating)).filter(VehicleReview.vehicle_id == vehicle_id)
        )
        avg = avg_result.scalar()

        count_result = await self.db.execute(
            select(func.count(VehicleReview.id)).filter(VehicleReview.vehicle_id == vehicle_id)
        )
        count = count_result.scalar()

        vehicle = await self.get_by_id(vehicle_id)
        if vehicle:
            vehicle.rating = round(float(avg or 0), 2)
            vehicle.total_reviews = count or 0
            await self.db.commit()


class DriverRepository:
    """Repository for Driver CRUD operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, partner_id: UUID, data: Dict[str, Any]) -> Driver:
        driver = Driver(partner_id=partner_id, **data)
        self.db.add(driver)
        await self.db.commit()
        await self.db.refresh(driver)
        return driver

    async def get_by_id(self, driver_id: UUID) -> Optional[Driver]:
        result = await self.db.execute(select(Driver).filter(Driver.id == driver_id))
        return result.scalars().first()

    async def get_by_license(self, license_number: str) -> Optional[Driver]:
        result = await self.db.execute(
            select(Driver).filter(Driver.license_number == license_number)
        )
        return result.scalars().first()

    async def list_by_partner(self, partner_id: UUID, page: int = 1, limit: int = 20):
        query = select(Driver).filter(Driver.partner_id == partner_id)

        count_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar()

        result = await self.db.execute(query.offset((page - 1) * limit).limit(limit))
        drivers = result.scalars().all()
        return drivers, total

    async def update(self, driver: Driver, data: Dict[str, Any]) -> Driver:
        for key, value in data.items():
            if value is not None:
                setattr(driver, key, value)
        driver.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(driver)
        return driver

    async def update_status(self, driver: Driver, status) -> Driver:
        driver.status = status
        driver.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(driver)
        return driver

    async def delete(self, driver: Driver):
        await self.db.delete(driver)
        await self.db.commit()


class VehicleDocumentRepository:
    """Repository for VehicleDocument operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, vehicle_id: UUID, data: Dict[str, Any]) -> VehicleDocument:
        doc = VehicleDocument(vehicle_id=vehicle_id, **data)
        self.db.add(doc)
        await self.db.commit()
        await self.db.refresh(doc)
        return doc

    async def list_by_vehicle(self, vehicle_id: UUID) -> List[VehicleDocument]:
        result = await self.db.execute(
            select(VehicleDocument).filter(VehicleDocument.vehicle_id == vehicle_id)
        )
        return result.scalars().all()

    async def get_by_id(self, doc_id: UUID) -> Optional[VehicleDocument]:
        result = await self.db.execute(
            select(VehicleDocument).filter(VehicleDocument.id == doc_id)
        )
        return result.scalars().first()