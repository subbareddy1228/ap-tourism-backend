import random
import string
from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.models.darshan import (
    DarshanBooking, PoojaBooking, PrasadamOrder, PrasadamOrderItem
)
from src.repositories.darshan_repo import DarshanRepository
from src.schemas.darshan import (
    DarshanCheckAvailabilityRequest, DarshanCheckAvailabilityResponse,
    DarshanBookRequest, DarshanBookingResponse,
    PoojaBookRequest, PoojaBookingResponse,
    PrasadamOrderRequest, PrasadamOrderResponse,
)


def generate_reference(prefix: str) -> str:
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"{prefix}-{suffix}"


class DarshanService:

    def __init__(self, db: Session, redis_client=None):
        self.db = db
        self.redis = redis_client
        self.repo = DarshanRepository(db)

    # ─────────────────────────────────────────────
    # Darshan Types
    # ─────────────────────────────────────────────

    def get_darshan_types(self, temple_id: UUID):
        return self.repo.get_darshan_types(temple_id)

    def get_darshan_type_detail(self, temple_id: UUID, type_id: UUID):
        darshan_type = self.repo.get_darshan_type_by_id(temple_id, type_id)
        if not darshan_type:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Darshan type not found")
        return darshan_type

    # ─────────────────────────────────────────────
    # Darshan Slots
    # ─────────────────────────────────────────────

    def get_darshan_slots(self, temple_id: UUID):
        cache_key = f"darshan_slots:{temple_id}"
        if self.redis:
            cached = self.redis.get(cache_key)
            if cached:
                return cached
        slots = self.repo.get_darshan_slots(temple_id)
        return slots

    def get_darshan_slots_by_date(self, temple_id: UUID, slot_date: date):
        return self.repo.get_darshan_slots_by_date(temple_id, slot_date)

    # ─────────────────────────────────────────────
    # Darshan Booking
    # ─────────────────────────────────────────────

    def check_availability(self, temple_id: UUID, req: DarshanCheckAvailabilityRequest):
        slot = self.repo.get_slot_by_id(req.slot_id)
        if not slot:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Slot not found")

        available_quota = slot.total_quota - slot.booked_count
        is_available = available_quota >= req.num_persons

        return DarshanCheckAvailabilityResponse(
            slot_id=req.slot_id,
            available=is_available,
            available_quota=available_quota,
            message="Slots available" if is_available else "Not enough slots available"
        )

    def book_darshan(self, temple_id: UUID, user_id: UUID, req: DarshanBookRequest):
        slot = self.repo.get_slot_by_id(req.slot_id)
        if not slot:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Slot not found")

        available_quota = slot.total_quota - slot.booked_count
        if available_quota < req.num_persons:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not enough slots available")

        # Redis lock to prevent double booking
        lock_key = f"slot_lock:{req.slot_id}"
        if self.redis:
            lock = self.redis.set(lock_key, str(user_id), nx=True, ex=900)  # 15 min lock
            if not lock:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slot is being booked by another user")

        darshan_type = self.repo.get_darshan_type_by_id(temple_id, slot.darshan_type_id)
        total_amount = (darshan_type.price if darshan_type else 0.0) * req.num_persons

        booking = DarshanBooking(
            temple_id=temple_id,
            slot_id=req.slot_id,
            user_id=user_id,
            booking_reference=generate_reference("DRS"),
            num_persons=req.num_persons,
            total_amount=total_amount,
            pilgrim_details=[p.dict() for p in req.pilgrim_details] if req.pilgrim_details else [],
        )

        created = self.repo.create_darshan_booking(booking)
        self.repo.increment_slot_booking(req.slot_id)

        # Release Redis lock
        if self.redis:
            self.redis.delete(lock_key)

        return created

    def get_darshan_booking(self, temple_id: UUID, booking_id: UUID):
        booking = self.repo.get_darshan_booking(temple_id, booking_id)
        if not booking:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
        return booking

    # ─────────────────────────────────────────────
    # Pooja Services
    # ─────────────────────────────────────────────

    def get_pooja_services(self, temple_id: UUID):
        return self.repo.get_pooja_services(temple_id)

    def get_pooja_service_detail(self, temple_id: UUID, service_id: UUID):
        service = self.repo.get_pooja_service_by_id(temple_id, service_id)
        if not service:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pooja service not found")
        return service

    def get_pooja_slots(self, temple_id: UUID, service_id: UUID):
        self.get_pooja_service_detail(temple_id, service_id)
        return self.repo.get_pooja_slots(service_id)

    def book_pooja(self, temple_id: UUID, service_id: UUID, user_id: UUID, req: PoojaBookRequest):
        service = self.repo.get_pooja_service_by_id(temple_id, service_id)
        if not service:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pooja service not found")

        slot = self.repo.get_pooja_slot_by_id(req.slot_id)
        if not slot:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pooja slot not found")

        total_amount = service.price * req.num_persons

        booking = PoojaBooking(
            temple_id=temple_id,
            service_id=service_id,
            slot_id=req.slot_id,
            user_id=user_id,
            booking_reference=generate_reference("POJ"),
            num_persons=req.num_persons,
            total_amount=total_amount,
            special_requests=req.special_requests,
        )

        return self.repo.create_pooja_booking(booking)

    # ─────────────────────────────────────────────
    # Prasadam
    # ─────────────────────────────────────────────

    def get_prasadam_items(self, temple_id: UUID):
        return self.repo.get_prasadam_items(temple_id)

    def get_prasadam_item(self, temple_id: UUID, item_id: UUID):
        item = self.repo.get_prasadam_item_by_id(temple_id, item_id)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prasadam item not found")
        return item

    def order_prasadam(self, temple_id: UUID, user_id: UUID, req: PrasadamOrderRequest):
        total_amount = 0.0
        order_items = []

        for item_req in req.items:
            item = self.repo.get_prasadam_item_by_id(temple_id, item_req.item_id)
            if not item:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Item {item_req.item_id} not found")
            subtotal = item.price * item_req.quantity
            total_amount += subtotal
            order_items.append(PrasadamOrderItem(
                item_id=item_req.item_id,
                quantity=item_req.quantity,
                unit_price=item.price,
                subtotal=subtotal,
            ))

        order = PrasadamOrder(
            temple_id=temple_id,
            user_id=user_id,
            order_reference=generate_reference("PRS"),
            total_amount=total_amount,
            pickup_date=req.pickup_date,
        )
        order.items = order_items

        return self.repo.create_prasadam_order(order)

    def get_my_prasadam_orders(self, temple_id: UUID, user_id: UUID):
        return self.repo.get_prasadam_orders_by_user(temple_id, user_id)