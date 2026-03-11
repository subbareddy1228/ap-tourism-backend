from datetime import date
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.models.darshan import (
    DarshanTypeModel, DarshanSlot, DarshanBooking,
    PoojaService, PoojaSlot, PoojaBooking,
    PrasadamItem, PrasadamOrder, PrasadamOrderItem,
)
from src.models.temple import BookingStatus


class DarshanRepository:

    def __init__(self, db: Session):
        self.db = db

    # ─────────────────────────────────────────────
    # Darshan Types
    # ─────────────────────────────────────────────

    def get_darshan_types(self, temple_id: UUID) -> List[DarshanTypeModel]:
        return self.db.query(DarshanTypeModel).filter(
            DarshanTypeModel.temple_id == temple_id,
            DarshanTypeModel.is_active == True
        ).all()

    def get_darshan_type_by_id(self, temple_id: UUID, type_id: UUID) -> Optional[DarshanTypeModel]:
        return self.db.query(DarshanTypeModel).filter(
            DarshanTypeModel.id == type_id,
            DarshanTypeModel.temple_id == temple_id
        ).first()

    # ─────────────────────────────────────────────
    # Darshan Slots
    # ─────────────────────────────────────────────

    def get_darshan_slots(self, temple_id: UUID) -> List[DarshanSlot]:
        from datetime import datetime, timedelta
        today = datetime.utcnow().date()
        end_date = today + timedelta(days=30)
        return self.db.query(DarshanSlot).filter(
            DarshanSlot.temple_id == temple_id,
            DarshanSlot.slot_date >= today,
            DarshanSlot.slot_date <= end_date,
            DarshanSlot.is_active == True
        ).order_by(DarshanSlot.slot_date, DarshanSlot.start_time).all()

    def get_darshan_slots_by_date(self, temple_id: UUID, slot_date: date) -> List[DarshanSlot]:
        return self.db.query(DarshanSlot).filter(
            DarshanSlot.temple_id == temple_id,
            DarshanSlot.slot_date == slot_date,
            DarshanSlot.is_active == True
        ).order_by(DarshanSlot.start_time).all()

    def get_slot_by_id(self, slot_id: UUID) -> Optional[DarshanSlot]:
        return self.db.query(DarshanSlot).filter(DarshanSlot.id == slot_id).first()

    def increment_slot_booking(self, slot_id: UUID) -> None:
        slot = self.get_slot_by_id(slot_id)
        if slot:
            slot.booked_count += 1
            self.db.commit()

    # ─────────────────────────────────────────────
    # Darshan Bookings
    # ─────────────────────────────────────────────

    def create_darshan_booking(self, booking: DarshanBooking) -> DarshanBooking:
        self.db.add(booking)
        self.db.commit()
        self.db.refresh(booking)
        return booking

    def get_darshan_booking(self, temple_id: UUID, booking_id: UUID) -> Optional[DarshanBooking]:
        return self.db.query(DarshanBooking).filter(
            DarshanBooking.id == booking_id,
            DarshanBooking.temple_id == temple_id
        ).first()

    # ─────────────────────────────────────────────
    # Pooja Services
    # ─────────────────────────────────────────────

    def get_pooja_services(self, temple_id: UUID) -> List[PoojaService]:
        return self.db.query(PoojaService).filter(
            PoojaService.temple_id == temple_id,
            PoojaService.is_active == True
        ).all()

    def get_pooja_service_by_id(self, temple_id: UUID, service_id: UUID) -> Optional[PoojaService]:
        return self.db.query(PoojaService).filter(
            PoojaService.id == service_id,
            PoojaService.temple_id == temple_id
        ).first()

    def get_pooja_slots(self, service_id: UUID) -> List[PoojaSlot]:
        from datetime import datetime
        today = datetime.utcnow().date()
        return self.db.query(PoojaSlot).filter(
            PoojaSlot.service_id == service_id,
            PoojaSlot.slot_date >= today,
            PoojaSlot.is_active == True
        ).order_by(PoojaSlot.slot_date, PoojaSlot.start_time).all()

    def get_pooja_slot_by_id(self, slot_id: UUID) -> Optional[PoojaSlot]:
        return self.db.query(PoojaSlot).filter(PoojaSlot.id == slot_id).first()

    def create_pooja_booking(self, booking: PoojaBooking) -> PoojaBooking:
        self.db.add(booking)
        self.db.commit()
        self.db.refresh(booking)
        return booking

    # ─────────────────────────────────────────────
    # Prasadam
    # ─────────────────────────────────────────────

    def get_prasadam_items(self, temple_id: UUID) -> List[PrasadamItem]:
        return self.db.query(PrasadamItem).filter(
            PrasadamItem.temple_id == temple_id,
            PrasadamItem.is_available == True
        ).all()

    def get_prasadam_item_by_id(self, temple_id: UUID, item_id: UUID) -> Optional[PrasadamItem]:
        return self.db.query(PrasadamItem).filter(
            PrasadamItem.id == item_id,
            PrasadamItem.temple_id == temple_id
        ).first()

    def create_prasadam_order(self, order: PrasadamOrder) -> PrasadamOrder:
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order

    def get_prasadam_orders_by_user(self, temple_id: UUID, user_id: UUID) -> List[PrasadamOrder]:
        return self.db.query(PrasadamOrder).filter(
            PrasadamOrder.temple_id == temple_id,
            PrasadamOrder.user_id == user_id
        ).order_by(PrasadamOrder.created_at.desc()).all()