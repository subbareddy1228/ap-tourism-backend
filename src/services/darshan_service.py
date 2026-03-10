import json
import uuid
import random
import string
from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from src.repositories.darshan_repo import DarshanRepository
from src.repositories.temple_repo import TempleRepository
from src.schemas.darshan import (
    DarshanTypeResponse, DarshanSlotResponse,
    DarshanCheckAvailabilityRequest, DarshanCheckAvailabilityResponse,
    DarshanBookRequest, DarshanBookingResponse,
    PoojaServiceResponse, PoojaSlotResponse,
    PoojaBookRequest, PoojaBookingResponse,
    PrasadamItemResponse, PrasadamOrderRequest, PrasadamOrderResponse,
)
from src.models.temple import BookingStatus
from src.core.exceptions import (
    NotFoundException, ConflictException, BadRequestException
)

SLOT_LOCK_TTL = 15 * 60   # 15 minutes in seconds
DARSHAN_SLOT_CACHE_TTL = 120  # 2 minutes


def _generate_booking_reference(prefix: str = "APT") -> str:
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"{prefix}-{suffix}"


class DarshanService:

    def __init__(self, db: Session, redis_client=None):
        self.repo = DarshanRepository(db)
        self.temple_repo = TempleRepository(db)
        self.redis = redis_client

    # ─────────────────────────────────────────────
    # Redis Helpers
    # ─────────────────────────────────────────────

    def _lock_key(self, slot_id: UUID) -> str:
        return f"slot_lock:{slot_id}"

    def _cache_key_slots(self, temple_id: UUID) -> str:
        return f"darshan_slots:{temple_id}:30days"

    def _acquire_slot_lock(self, slot_id: UUID, booking_id: UUID) -> bool:
        """Returns True if lock acquired, False if already locked."""
        if not self.redis:
            return True  # No Redis: allow without lock (dev mode)
        key = self._lock_key(slot_id)
        result = self.redis.set(key, str(booking_id), nx=True, ex=SLOT_LOCK_TTL)
        return result is not None

    def _release_slot_lock(self, slot_id: UUID) -> None:
        if self.redis:
            self.redis.delete(self._lock_key(slot_id))

    def _invalidate_slot_cache(self, temple_id: UUID) -> None:
        if self.redis:
            self.redis.delete(self._cache_key_slots(temple_id))

    # ─────────────────────────────────────────────
    # Darshan Types
    # ─────────────────────────────────────────────

    def get_darshan_types(self, temple_id: UUID) -> List[DarshanTypeResponse]:
        self._assert_temple_exists(temple_id)
        types = self.repo.get_darshan_types(temple_id)
        return [DarshanTypeResponse.model_validate(t) for t in types]

    def get_darshan_type_detail(self, temple_id: UUID, type_id: UUID) -> DarshanTypeResponse:
        self._assert_temple_exists(temple_id)
        dt = self.repo.get_darshan_type_by_id(type_id)
        if not dt or dt.temple_id != temple_id:
            raise NotFoundException(f"Darshan type {type_id} not found for this temple")
        return DarshanTypeResponse.model_validate(dt)

    # ─────────────────────────────────────────────
    # Darshan Slots
    # ─────────────────────────────────────────────

    def get_darshan_slots(self, temple_id: UUID) -> List[DarshanSlotResponse]:
        """Next 30 days - cached for 2 minutes."""
        self._assert_temple_exists(temple_id)

        if self.redis:
            cache_key = self._cache_key_slots(temple_id)
            cached = self.redis.get(cache_key)
            if cached:
                return json.loads(cached)

        slots = self.repo.get_slots_next_30_days(temple_id)
        result = [self._slot_to_response(s) for s in slots]

        if self.redis:
            self.redis.setex(
                self._cache_key_slots(temple_id),
                DARSHAN_SLOT_CACHE_TTL,
                json.dumps([r.model_dump(mode="json") for r in result]),
            )
        return result

    def get_darshan_slots_by_date(
        self, temple_id: UUID, slot_date: date
    ) -> List[DarshanSlotResponse]:
        self._assert_temple_exists(temple_id)
        slots = self.repo.get_slots_by_date(temple_id, slot_date)
        return [self._slot_to_response(s) for s in slots]

    def _slot_to_response(self, slot) -> DarshanSlotResponse:
        return DarshanSlotResponse(
            id=slot.id,
            temple_id=slot.temple_id,
            darshan_type_id=slot.darshan_type_id,
            slot_date=slot.slot_date,
            start_time=str(slot.start_time),
            end_time=str(slot.end_time),
            total_quota=slot.total_quota,
            booked_count=slot.booked_count,
            available_count=slot.available_count,
            is_full=slot.is_full,
        )

    # ─────────────────────────────────────────────
    # Check Availability
    # ─────────────────────────────────────────────

    def check_availability(
        self, temple_id: UUID, req: DarshanCheckAvailabilityRequest
    ) -> DarshanCheckAvailabilityResponse:
        self._assert_temple_exists(temple_id)
        slot = self.repo.get_slot_by_id(req.slot_id)
        if not slot or slot.temple_id != temple_id:
            raise NotFoundException("Slot not found for this temple")

        available = slot.available_count >= req.devotees_count
        return DarshanCheckAvailabilityResponse(
            slot_id=req.slot_id,
            available=available,
            available_count=slot.available_count,
            requested_count=req.devotees_count,
            message="Slot is available" if available else "Insufficient quota for requested devotees",
        )

    # ─────────────────────────────────────────────
    # Book Darshan
    # ─────────────────────────────────────────────

    def book_darshan(
        self, temple_id: UUID, user_id: UUID, req: DarshanBookRequest
    ) -> DarshanBookingResponse:
        self._assert_temple_exists(temple_id)

        slot = self.repo.get_slot_by_id(req.slot_id)
        if not slot or slot.temple_id != temple_id:
            raise NotFoundException("Slot not found for this temple")

        if slot.available_count < req.devotees_count:
            raise ConflictException("Not enough quota available in this slot")

        # Lock slot in Redis for 15 minutes
        booking_id = uuid.uuid4()
        locked = self._acquire_slot_lock(req.slot_id, booking_id)
        if not locked:
            raise ConflictException(
                "Slot is currently being booked by another user. Please try again shortly."
            )

        try:
            darshan_type = self.repo.get_darshan_type_by_id(slot.darshan_type_id)
            total_amount = Decimal(str(darshan_type.price)) * req.devotees_count

            booking_data = {
                "id": booking_id,
                "temple_id": temple_id,
                "slot_id": req.slot_id,
                "user_id": user_id,
                "devotees_count": req.devotees_count,
                "status": BookingStatus.PENDING,
                "total_amount": total_amount,
                "booking_reference": _generate_booking_reference("DRS"),
                "notes": req.notes,
            }
            booking = self.repo.create_darshan_booking(booking_data)
            self.temple_repo.increment_booking_count(temple_id)
            self._invalidate_slot_cache(temple_id)
            return DarshanBookingResponse.model_validate(booking)

        except Exception:
            # Release lock on failure so slot is not stuck
            self._release_slot_lock(req.slot_id)
            raise

    def get_darshan_booking(
        self, temple_id: UUID, booking_id: UUID
    ) -> DarshanBookingResponse:
        booking = self.repo.get_darshan_booking(booking_id)
        if not booking or booking.temple_id != temple_id:
            raise NotFoundException("Booking not found")
        return DarshanBookingResponse.model_validate(booking)

    # ─────────────────────────────────────────────
    # Pooja Services
    # ─────────────────────────────────────────────

    def get_pooja_services(self, temple_id: UUID) -> List[PoojaServiceResponse]:
        self._assert_temple_exists(temple_id)
        services = self.repo.get_pooja_services(temple_id)
        return [PoojaServiceResponse.model_validate(s) for s in services]

    def get_pooja_service_detail(
        self, temple_id: UUID, service_id: UUID
    ) -> PoojaServiceResponse:
        self._assert_temple_exists(temple_id)
        service = self.repo.get_pooja_service_by_id(service_id)
        if not service or service.temple_id != temple_id:
            raise NotFoundException("Pooja service not found")
        return PoojaServiceResponse.model_validate(service)

    def get_pooja_slots(
        self, temple_id: UUID, service_id: UUID
    ) -> List[PoojaSlotResponse]:
        service = self.repo.get_pooja_service_by_id(service_id)
        if not service or service.temple_id != temple_id:
            raise NotFoundException("Pooja service not found")
        slots = self.repo.get_pooja_slots(service_id)
        return [
            PoojaSlotResponse(
                id=s.id,
                pooja_service_id=s.pooja_service_id,
                slot_date=s.slot_date,
                start_time=str(s.start_time),
                end_time=str(s.end_time),
                total_quota=s.total_quota,
                booked_count=s.booked_count,
                available_count=s.available_count,
            )
            for s in slots
        ]

    def book_pooja(
        self, temple_id: UUID, service_id: UUID, user_id: UUID, req: PoojaBookRequest
    ) -> PoojaBookingResponse:
        service = self.repo.get_pooja_service_by_id(service_id)
        if not service or service.temple_id != temple_id:
            raise NotFoundException("Pooja service not found")

        slot = self.repo.get_pooja_slot_by_id(req.slot_id)
        if not slot or slot.pooja_service_id != service_id:
            raise NotFoundException("Pooja slot not found")
        if slot.available_count < 1:
            raise ConflictException("Pooja slot is fully booked")

        booking_data = {
            "pooja_service_id": service_id,
            "slot_id": req.slot_id,
            "user_id": user_id,
            "status": BookingStatus.PENDING,
            "total_amount": service.price,
            "booking_reference": _generate_booking_reference("POO"),
        }
        booking = self.repo.create_pooja_booking(booking_data)
        return PoojaBookingResponse.model_validate(booking)

    # ─────────────────────────────────────────────
    # Prasadam
    # ─────────────────────────────────────────────

    def get_prasadam_items(self, temple_id: UUID) -> List[PrasadamItemResponse]:
        self._assert_temple_exists(temple_id)
        items = self.repo.get_prasadam_items(temple_id)
        return [PrasadamItemResponse.model_validate(i) for i in items]

    def get_prasadam_item(self, temple_id: UUID, item_id: UUID) -> PrasadamItemResponse:
        item = self.repo.get_prasadam_item_by_id(item_id)
        if not item or item.temple_id != temple_id:
            raise NotFoundException("Prasadam item not found")
        return PrasadamItemResponse.model_validate(item)

    def order_prasadam(
        self, temple_id: UUID, user_id: UUID, req: PrasadamOrderRequest
    ) -> PrasadamOrderResponse:
        self._assert_temple_exists(temple_id)

        total_amount = Decimal("0.00")
        items_data = []
        for req_item in req.items:
            item = self.repo.get_prasadam_item_by_id(req_item.prasadam_item_id)
            if not item or item.temple_id != temple_id:
                raise NotFoundException(f"Prasadam item {req_item.prasadam_item_id} not found")
            if not item.is_available:
                raise BadRequestException(f"{item.name} is currently unavailable")
            line_total = Decimal(str(item.price)) * req_item.quantity
            total_amount += line_total
            items_data.append({
                "prasadam_item_id": item.id,
                "quantity": req_item.quantity,
                "unit_price": item.price,
            })

        order_data = {
            "status": BookingStatus.PENDING,
            "total_amount": total_amount,
            "pickup_date": req.pickup_date,
            "booking_reference": _generate_booking_reference("PRS"),
        }
        order = self.repo.create_prasadam_order(temple_id, user_id, order_data, items_data)
        return PrasadamOrderResponse.model_validate(order)

    def get_my_prasadam_orders(
        self, temple_id: UUID, user_id: UUID
    ) -> List[PrasadamOrderResponse]:
        orders = self.repo.get_prasadam_orders_by_user(temple_id, user_id)
        return [PrasadamOrderResponse.model_validate(o) for o in orders]

    # ─────────────────────────────────────────────
    # Internal
    # ─────────────────────────────────────────────

    def _assert_temple_exists(self, temple_id: UUID) -> None:
        temple = self.temple_repo.get_by_id(temple_id)
        if not temple:
            raise NotFoundException(f"Temple {temple_id} not found")