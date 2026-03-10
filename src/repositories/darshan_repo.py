from datetime import date, timedelta
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
        return (
            self.db.query(DarshanTypeModel)
            .filter(DarshanTypeModel.temple_id == temple_id, DarshanTypeModel.is_active == True)
            .all()
        )

    def get_darshan_type_by_id(self, type_id: UUID) -> Optional[DarshanTypeModel]:
        return self.db.query(DarshanTypeModel).filter(DarshanTypeModel.id == type_id).first()

    # ─────────────────────────────────────────────
    # Darshan Slots
    # ─────────────────────────────────────────────

    def get_slots_next_30_days(self, temple_id: UUID) -> List[DarshanSlot]:
        today = date.today()
        end_date = today + timedelta(days=30)
        return (
            self.db.query(DarshanSlot)
            .filter(
                DarshanSlot.temple_id == temple_id,
                DarshanSlot.slot_date >= today,
                DarshanSlot.slot_date <= end_date,
                DarshanSlot.is_active == True,
            )
            .order_by(DarshanSlot.slot_date, DarshanSlot.start_time)
            .all()
        )

    def get_slots_by_date(self, temple_id: UUID, slot_date: date) -> List[DarshanSlot]:
        return (
            self.db.query(DarshanSlot)
            .filter(
                DarshanSlot.temple_id == temple_id,
                DarshanSlot.slot_date == slot_date,
                DarshanSlot.is_active == True,
            )
            .order_by(DarshanSlot.start_time)
            .all()
        )

    def get_slot_by_id(self, slot_id: UUID) -> Optional[DarshanSlot]:
        return self.db.query(DarshanSlot).filter(DarshanSlot.id == slot_id).first()

    def check_slot_availability(self, slot_id: UUID, devotees_count: int) -> bool:
        slot = self.get_slot_by_id(slot_id)
        if not slot:
            return False
        return slot.available_count >= devotees_count

    # ─────────────────────────────────────────────
    # Darshan Bookings
    # ─────────────────────────────────────────────

    def create_darshan_booking(self, booking_data: dict) -> DarshanBooking:
        booking = DarshanBooking(**booking_data)
        self.db.add(booking)
        # Increment booked_count on slot
        self.db.query(DarshanSlot).filter(DarshanSlot.id == booking_data["slot_id"]).update(
            {DarshanSlot.booked_count: DarshanSlot.booked_count + booking_data["devotees_count"]}
        )
        self.db.commit()
        self.db.refresh(booking)
        return booking

    def get_darshan_booking(self, booking_id: UUID) -> Optional[DarshanBooking]:
        return self.db.query(DarshanBooking).filter(DarshanBooking.id == booking_id).first()

    def update_booking_status(
        self, booking_id: UUID, status: BookingStatus, payment_id: Optional[str] = None
    ) -> Optional[DarshanBooking]:
        booking = self.get_darshan_booking(booking_id)
        if not booking:
            return None
        booking.status = status
        if payment_id:
            booking.payment_id = payment_id
        self.db.commit()
        self.db.refresh(booking)
        return booking

    # ─────────────────────────────────────────────
    # Pooja Services
    # ─────────────────────────────────────────────

    def get_pooja_services(self, temple_id: UUID) -> List[PoojaService]:
        return (
            self.db.query(PoojaService)
            .filter(PoojaService.temple_id == temple_id, PoojaService.is_active == True)
            .all()
        )

    def get_pooja_service_by_id(self, service_id: UUID) -> Optional[PoojaService]:
        return self.db.query(PoojaService).filter(PoojaService.id == service_id).first()

    def get_pooja_slots(self, service_id: UUID) -> List[PoojaSlot]:
        today = date.today()
        return (
            self.db.query(PoojaSlot)
            .filter(
                PoojaSlot.pooja_service_id == service_id,
                PoojaSlot.slot_date >= today,
                PoojaSlot.is_active == True,
            )
            .order_by(PoojaSlot.slot_date, PoojaSlot.start_time)
            .all()
        )

    def get_pooja_slot_by_id(self, slot_id: UUID) -> Optional[PoojaSlot]:
        return self.db.query(PoojaSlot).filter(PoojaSlot.id == slot_id).first()

    def create_pooja_booking(self, booking_data: dict) -> PoojaBooking:
        booking = PoojaBooking(**booking_data)
        self.db.add(booking)
        self.db.query(PoojaSlot).filter(PoojaSlot.id == booking_data["slot_id"]).update(
            {PoojaSlot.booked_count: PoojaSlot.booked_count + 1}
        )
        self.db.commit()
        self.db.refresh(booking)
        return booking

    def get_pooja_booking(self, booking_id: UUID) -> Optional[PoojaBooking]:
        return self.db.query(PoojaBooking).filter(PoojaBooking.id == booking_id).first()

    # ─────────────────────────────────────────────
    # Prasadam
    # ─────────────────────────────────────────────

    def get_prasadam_items(self, temple_id: UUID) -> List[PrasadamItem]:
        return (
            self.db.query(PrasadamItem)
            .filter(PrasadamItem.temple_id == temple_id, PrasadamItem.is_available == True)
            .all()
        )

    def get_prasadam_item_by_id(self, item_id: UUID) -> Optional[PrasadamItem]:
        return self.db.query(PrasadamItem).filter(PrasadamItem.id == item_id).first()

    def create_prasadam_order(
        self, temple_id: UUID, user_id: UUID, order_data: dict, items_data: list
    ) -> PrasadamOrder:
        order = PrasadamOrder(temple_id=temple_id, user_id=user_id, **order_data)
        self.db.add(order)
        self.db.flush()  # get order.id before committing
        for item in items_data:
            order_item = PrasadamOrderItem(order_id=order.id, **item)
            self.db.add(order_item)
        self.db.commit()
        self.db.refresh(order)
        return order

    def get_prasadam_orders_by_user(
        self, temple_id: UUID, user_id: UUID
    ) -> List[PrasadamOrder]:
        return (
            self.db.query(PrasadamOrder)
            .filter(
                PrasadamOrder.temple_id == temple_id,
                PrasadamOrder.user_id == user_id,
            )
            .order_by(PrasadamOrder.created_at.desc())
            .all()
        )

    def get_prasadam_order_by_id(self, order_id: UUID) -> Optional[PrasadamOrder]:
        return self.db.query(PrasadamOrder).filter(PrasadamOrder.id == order_id).first()