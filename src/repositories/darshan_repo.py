from datetime import date, timedelta
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.models.darshan import (
    DarshanType, DarshanSlot, DarshanBooking,
    PoojaService, PoojaSlot, PoojaBooking,
    PrasadamItem, PrasadamOrder,
)


class DarshanRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    # ─────────────────────────────────────────────
    # Darshan Types
    # ─────────────────────────────────────────────
    async def get_darshan_types(self, temple_id: UUID) -> List[DarshanType]:
        result = await self.db.execute(
            select(DarshanType).where(
                DarshanType.temple_id == temple_id,
                DarshanType.is_active == True,
            )
        )
        return result.scalars().all()

    async def get_darshan_type_by_id(self, temple_id: UUID, type_id: UUID) -> Optional[DarshanType]:
        result = await self.db.execute(
            select(DarshanType).where(
                DarshanType.id == type_id,
                DarshanType.temple_id == temple_id,
                DarshanType.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    # ─────────────────────────────────────────────
    # Darshan Slots
    # ─────────────────────────────────────────────
    async def get_darshan_slots(self, temple_id: UUID) -> List[DarshanSlot]:
        today = date.today()
        end_date = today + timedelta(days=30)

        result = await self.db.execute(
            select(DarshanSlot).where(
                DarshanSlot.temple_id == temple_id,
                DarshanSlot.slot_date >= today,
                DarshanSlot.slot_date <= end_date,
                DarshanSlot.is_active == True,
            ).order_by(DarshanSlot.slot_date, DarshanSlot.start_time)
        )
        return result.scalars().all()

    async def get_darshan_slots_by_date(self, temple_id: UUID, slot_date: date) -> List[DarshanSlot]:
        result = await self.db.execute(
            select(DarshanSlot).where(
                DarshanSlot.temple_id == temple_id,
                DarshanSlot.slot_date == slot_date,
                DarshanSlot.is_active == True,
            ).order_by(DarshanSlot.start_time)
        )
        return result.scalars().all()

    async def get_slot_by_id(self, slot_id: UUID) -> Optional[DarshanSlot]:
        result = await self.db.execute(
            select(DarshanSlot).where(
                DarshanSlot.id == slot_id,
                DarshanSlot.is_active == True
            )
        )
        return result.scalar_one_or_none()

    # ─────────────────────────────────────────────
    # Darshan Bookings
    # ─────────────────────────────────────────────
    async def increment_slot_booking(self, slot_id: UUID, num_persons: int) -> None:
        slot = await self.get_slot_by_id(slot_id)
        if slot:
            slot.booked_count += num_persons
            await self.db.commit()

    async def create_darshan_booking(self, booking: DarshanBooking) -> DarshanBooking:
        self.db.add(booking)
        await self.db.commit()
        await self.db.refresh(booking)
        return booking

    async def get_darshan_booking(self, temple_id: UUID, booking_id: UUID) -> Optional[DarshanBooking]:
        result = await self.db.execute(
            select(DarshanBooking).where(
                DarshanBooking.id == booking_id,
                DarshanBooking.temple_id == temple_id,
            )
        )
        return result.scalar_one_or_none()

    # ─────────────────────────────────────────────
    # Pooja Services
    # ─────────────────────────────────────────────
    async def get_pooja_services(self, temple_id: UUID) -> List[PoojaService]:
        result = await self.db.execute(
            select(PoojaService).where(
                PoojaService.temple_id == temple_id,
                PoojaService.is_active == True,
            )
        )
        return result.scalars().all()

    async def get_pooja_service_by_id(self, temple_id: UUID, service_id: UUID) -> Optional[PoojaService]:
        result = await self.db.execute(
            select(PoojaService).where(
                PoojaService.id == service_id,
                PoojaService.temple_id == temple_id,
                PoojaService.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    # ─────────────────────────────────────────────
    # Pooja Slots
    # ─────────────────────────────────────────────
    async def get_pooja_slots(self, service_id: UUID) -> List[PoojaSlot]:
        result = await self.db.execute(
            select(PoojaSlot).where(
                PoojaSlot.pooja_service_id == service_id,
                PoojaSlot.slot_date >= date.today(),
                PoojaSlot.is_active == True,
            ).order_by(PoojaSlot.slot_date, PoojaSlot.start_time)
        )
        return result.scalars().all()

    async def get_pooja_slot_by_id(self, slot_id: UUID) -> Optional[PoojaSlot]:
        result = await self.db.execute(
            select(PoojaSlot).where(
                PoojaSlot.id == slot_id,
                PoojaSlot.is_active == True
            )
        )
        return result.scalar_one_or_none()

    async def increment_pooja_slot_booking(self, slot_id: UUID, num_persons: int) -> None:
        slot = await self.get_pooja_slot_by_id(slot_id)
        if slot:
            slot.booked_count += num_persons
            await self.db.commit()

    async def create_pooja_booking(self, booking: PoojaBooking) -> PoojaBooking:
        self.db.add(booking)
        await self.db.commit()
        await self.db.refresh(booking)
        return booking

    # ─────────────────────────────────────────────
    # Prasadam Items
    # ─────────────────────────────────────────────
    async def get_prasadam_items(self, temple_id: UUID) -> List[PrasadamItem]:
        result = await self.db.execute(
            select(PrasadamItem).where(
                PrasadamItem.temple_id == temple_id,
                PrasadamItem.is_available == True,
            )
        )
        return result.scalars().all()

    async def get_prasadam_item_by_id(self, temple_id: UUID, item_id: UUID) -> Optional[PrasadamItem]:
        result = await self.db.execute(
            select(PrasadamItem).where(
                PrasadamItem.id == item_id,
                PrasadamItem.temple_id == temple_id,
            )
        )
        return result.scalar_one_or_none()

    # ─────────────────────────────────────────────
    # Prasadam Orders
    # ─────────────────────────────────────────────
    async def create_prasadam_order(self, order: PrasadamOrder) -> PrasadamOrder:
        self.db.add(order)
        await self.db.commit()

        result = await self.db.execute(
            select(PrasadamOrder)
            .options(selectinload(PrasadamOrder.items))
            .where(PrasadamOrder.id == order.id)
        )
        return result.scalar_one()

    async def get_prasadam_orders_by_user(self, temple_id: UUID, user_id: UUID) -> List[PrasadamOrder]:
        result = await self.db.execute(
            select(PrasadamOrder)
            .options(selectinload(PrasadamOrder.items))
            .where(
                PrasadamOrder.temple_id == temple_id,
                PrasadamOrder.user_id == user_id,
            )
            .order_by(PrasadamOrder.created_at.desc())
        )
        return result.scalars().all()