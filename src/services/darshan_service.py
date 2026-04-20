"""
services/darshan_service.py  —  Darshan / Pooja / Prasadam business logic

Bugs fixed vs project file:
──────────────────────────────────────────────────────────────────────────────
  BUG-1  get_redis() in endpoint used the synchronous `redis` library
         (import redis as redis_lib; redis_lib.from_url(...))  instead of the
         project-wide async redis client from core/redis.py.  Calling sync
         .ping() inside an async function blocks the event loop.  The service
         is now constructed via the proper async helper in the endpoint.
         (Fixed in endpoints/darshan.py; no change needed here — service
         receives whatever client is passed in.)

  BUG-2  book_darshan(): After Redis lock + DB re-read, the service called
         slot.booked_count += num_persons then await self.db.commit() — a
         plain in-Python mutation of a loaded ORM object.  If the same slot
         object was already in the session from the lock-path get_slot_by_id()
         call, this double-mutated the count.  Delegated to the atomic
         repo.increment_slot_booking() (UPDATE statement) instead.

  BUG-3  order_prasadam(): The service set order.items = order_items before
         calling repo.create_prasadam_order(order).  PrasadamOrderItem objects
         in order_items were never db.add()'d to the session, so the cascade
         never fired and items were silently dropped from the insert.
         Fixed: add each PrasadamOrderItem explicitly to the session before
         commit, and link them via order_id after the order is created.

  BUG-4  book_darshan(): The service set booking_id=None (commented out
         because the temple-side path has no master Booking).  This is now
         documented clearly and the model's nullable=True handles it.

  BUG-5  book_pooja(): Same double-commit issue — service mutated
         slot.booked_count in Python, but this was also done by
         repo.increment_pooja_slot_booking(). Removed the in-Python mutation;
         repo now owns the increment atomically.

  BUG-6  get_my_prasadam_orders() passed user_id correctly to repo — was
         already correct in original; no change.

All method signatures are identical to the original — no endpoint callers
need to change.
"""

from datetime import date
from uuid import UUID
from src.schemas.darshan import (PoojaSlotBulkGenerate, PrasadamItemCreate)
from src.models.darshan import (DarshanBooking, PoojaBooking, PoojaSlot, PrasadamOrder, PrasadamOrderItem,PrasadamItem) 
 
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.darshan import (
    DarshanBooking, PoojaBooking,
    PrasadamOrder, PrasadamOrderItem,
)
from src.repositories.darshan_repo import DarshanRepository
from src.core.exceptions import (
    BadRequestException,
    ConflictException,
    NotFoundException,
)
from src.schemas.darshan import (
    DarshanTypeResponse, DarshanSlotResponse,
    DarshanCheckAvailabilityRequest, DarshanCheckAvailabilityResponse,
    DarshanBookRequest, DarshanBookingResponse,
    PoojaServiceResponse, PoojaSlotResponse,
    PoojaBookRequest, PoojaBookingResponse,
    PrasadamItemResponse, PrasadamOrderRequest, PrasadamOrderResponse,
)

import logging

logger = logging.getLogger(__name__)


class DarshanService:

    def __init__(self, db: AsyncSession, redis_client=None):
        self.db    = db
        self.redis = redis_client
        self.repo  = DarshanRepository(db)

    # ── Cache helpers ─────────────────────────────────────────────────────────

    async def _cache_get(self, key: str):
        if not self.redis:
            return None
        try:
            import json
            cached = await self.redis.get(key)
            return json.loads(cached) if cached else None
        except Exception:
            return None

    async def _cache_set(self, key: str, data, ttl: int = 120) -> None:
        if not self.redis:
            return
        try:
            import json
            await self.redis.set(key, json.dumps(data, default=str), ex=ttl)
        except Exception:
            pass

    async def _cache_delete(self, key: str) -> None:
        if not self.redis:
            return
        try:
            await self.redis.delete(key)
        except Exception:
            pass

    # ── Darshan Types ─────────────────────────────────────────────────────────

    async def get_darshan_types(self, temple_id: UUID):
        types = await self.repo.get_darshan_types(temple_id)
        return [DarshanTypeResponse.model_validate(t) for t in types]

    async def get_darshan_type_detail(self, temple_id: UUID, type_id: UUID):
        dt = await self.repo.get_darshan_type_by_id(temple_id, type_id)
        if not dt:
            raise NotFoundException("Darshan type not found")
        return DarshanTypeResponse.model_validate(dt)

    # ── Darshan Slots ─────────────────────────────────────────────────────────

    async def get_darshan_slots(self, temple_id: UUID):
        """Returns slots for next 30 days. Cached for 2 minutes."""
        cache_key = f"darshan_slots:{temple_id}"
        cached = await self._cache_get(cache_key)
        if cached is not None:
            return cached

        slots  = await self.repo.get_darshan_slots(temple_id)
        result = [DarshanSlotResponse.model_validate(s).model_dump() for s in slots]
        await self._cache_set(cache_key, result, ttl=120)
        return result

    async def get_darshan_slots_by_date(self, temple_id: UUID, slot_date: date):
        slots = await self.repo.get_darshan_slots_by_date(temple_id, slot_date)
        return [DarshanSlotResponse.model_validate(s) for s in slots]

    # ── Check Availability ────────────────────────────────────────────────────

    async def check_availability(
        self, temple_id: UUID, req: DarshanCheckAvailabilityRequest
    ):
        slot = await self.repo.get_slot_by_id(req.slot_id)
        if not slot:
            raise NotFoundException("Slot not found")
        if str(slot.temple_id) != str(temple_id):
            raise BadRequestException("Slot does not belong to this temple")

        is_available = slot.available_count >= req.num_persons
        return DarshanCheckAvailabilityResponse(
            slot_id=req.slot_id,
            is_available=is_available,
            available_count=slot.available_count,
            requested_persons=req.num_persons,
            message="Slots available" if is_available else "Not enough slots available",
        )

    # ── Book Darshan ──────────────────────────────────────────────────────────

    async def book_darshan(
        self, temple_id: UUID, user_id: UUID, req: DarshanBookRequest
    ):
        """
        Temple-side darshan booking flow.

        STEP 1  — Acquire Redis distributed lock BEFORE any DB read so two
                  concurrent users cannot both see "available" and both book.
        STEP 2  — Fresh DB read AFTER acquiring the lock.
        STEP 3  — Create PENDING DarshanBooking (booking_id=None because this
                  path has no master Booking; see model nullable=True fix).
        STEP 4  — Atomically increment slot.booked_count via UPDATE statement.
        STEP 5  — Bust slot cache; leave lock alive for 15 min.

        The booking_service.book_darshan() path (full flow with Razorpay) is
        separate and creates a master Booking first, then sets booking_id.
        """
        lock_key = f"slot_lock:{req.slot_id}"

        # STEP 1 — acquire lock
        if self.redis:
            acquired = await self.redis.set(lock_key, str(user_id), nx=True, ex=900)
            if not acquired:
                raise ConflictException(
                    "Slot is currently being booked. Please try again in a moment."
                )

        try:
            # STEP 2 — fresh DB read after lock
            slot = await self.repo.get_slot_by_id(req.slot_id)
            if not slot:
                raise NotFoundException("Slot not found")
            if str(slot.temple_id) != str(temple_id):
                raise BadRequestException("Slot does not belong to this temple")
            if slot.available_count < req.num_persons:
                raise BadRequestException(
                    f"Only {slot.available_count} slots available for this time"
                )

            # STEP 3 — calculate price and create PENDING booking
            darshan_type = await self.repo.get_darshan_type_by_id(
                temple_id, slot.darshan_type_id
            )
            price_per_person = float(darshan_type.price) if darshan_type else 0.0
            total_price      = price_per_person * req.num_persons

            booking = DarshanBooking(
                # booking_id intentionally omitted (nullable=True in model) —
                # this temple-side path has no master Booking context.
                temple_id        = temple_id,
                darshan_slot_id  = req.slot_id,
                darshan_type_id  = slot.darshan_type_id,
                darshan_date     = slot.slot_date,
                darshan_time     = slot.start_time,
                num_persons      = req.num_persons,
                price_per_person = price_per_person,
                total_price      = total_price,
                devotee_details  = (
                    [p.model_dump() for p in req.pilgrim_details]
                    if req.pilgrim_details else []
                ),
            )
            created = await self.repo.create_darshan_booking(booking)

            # STEP 4 — atomic increment (BUG-2 FIX: was in-Python mutation)
            await self.repo.increment_slot_booking(req.slot_id, req.num_persons)

        finally:
            # STEP 5 — bust slot cache; lock released by Redis TTL
            await self._cache_delete(f"darshan_slots:{temple_id}")

        logger.info(
            "DarshanBooking created booking_id=%s temple=%s slot=%s persons=%d",
            created.id, temple_id, req.slot_id, req.num_persons,
        )
        return DarshanBookingResponse.model_validate(created)

    async def get_darshan_booking(self, temple_id: UUID, booking_id: UUID):
        booking = await self.repo.get_darshan_booking(temple_id, booking_id)
        if not booking:
            raise NotFoundException("Booking not found")
        return DarshanBookingResponse.model_validate(booking)

    # ── Pooja Services ────────────────────────────────────────────────────────

    async def get_pooja_services(self, temple_id: UUID):
        services = await self.repo.get_pooja_services(temple_id)
        return [PoojaServiceResponse.model_validate(s) for s in services]

    async def get_pooja_service_detail(self, temple_id: UUID, service_id: UUID):
        service = await self.repo.get_pooja_service_by_id(temple_id, service_id)
        if not service:
            raise NotFoundException("Pooja service not found")
        return PoojaServiceResponse.model_validate(service)

    async def get_pooja_slots(self, temple_id: UUID, service_id: UUID):
        await self.get_pooja_service_detail(temple_id, service_id)   # 404 guard
        slots = await self.repo.get_pooja_slots(service_id)
        return [PoojaSlotResponse.model_validate(s) for s in slots]

    # ── Book Pooja ────────────────────────────────────────────────────────────

    async def book_pooja(
        self,
        temple_id:  UUID,
        service_id: UUID,
        user_id:    UUID,
        req:        PoojaBookRequest,
    ):
        """
        Same lock-first flow as book_darshan.
        BUG-5 FIX: Removed in-Python slot.booked_count mutation; uses atomic
        repo.increment_pooja_slot_booking() instead.
        """
        service = await self.repo.get_pooja_service_by_id(temple_id, service_id)
        if not service:
            raise NotFoundException("Pooja service not found")

        lock_key = f"pooja_lock:{req.slot_id}"

        if self.redis:
            acquired = await self.redis.set(lock_key, str(user_id), nx=True, ex=900)
            if not acquired:
                raise ConflictException(
                    "This pooja slot is currently being booked. Please try again."
                )

        try:
            slot = await self.repo.get_pooja_slot_by_id(req.slot_id)
            if not slot:
                raise NotFoundException("Pooja slot not found")
            if slot.available_count < req.num_persons:
                raise BadRequestException(
                    f"Only {slot.available_count} slots available"
                )

            booking = PoojaBooking(
                # booking_id intentionally omitted (nullable=True in model)
                temple_id=temple_id,
                pooja_service_id=service_id,
                slot_id=req.slot_id,
                num_persons=req.num_persons,
                price=float(service.price or 0) * req.num_persons,
                devotee_names=(
                    [req.devotee_name] if req.devotee_name else []
                ),
                gothram=req.gothram,
                nakshatra=req.nakshatra,
                special_instructions=req.special_requests,
            )
            created = await self.repo.create_pooja_booking(booking)

            # Atomic increment (BUG-5 FIX)
            await self.repo.increment_pooja_slot_booking(req.slot_id, req.num_persons)

        finally:
            # Lock released by Redis TTL after 15 min
            pass

        logger.info(
            "PoojaBooking created booking_id=%s temple=%s service=%s",
            created.id, temple_id, service_id,
        )
        return PoojaBookingResponse.model_validate(created)

    # ── Prasadam Items ────────────────────────────────────────────────────────

    async def get_prasadam_items(self, temple_id: UUID):
        items = await self.repo.get_prasadam_items(temple_id)
        return [PrasadamItemResponse.model_validate(i) for i in items]

    async def get_prasadam_item(self, temple_id: UUID, item_id: UUID):
        item = await self.repo.get_prasadam_item_by_id(temple_id, item_id)
        if not item:
            raise NotFoundException("Prasadam item not found")
        return PrasadamItemResponse.model_validate(item)

    # ── Order Prasadam ────────────────────────────────────────────────────────

    async def order_prasadam(
        self, temple_id: UUID, user_id: UUID, req: PrasadamOrderRequest
    ):
        """
        BUG-3 FIX: Original set order.items = order_items before adding order
        to the session.  PrasadamOrderItem objects were never add()'d
        individually, so the SQLAlchemy cascade never fired and items were
        silently dropped from the INSERT.

        Fixed: create the PrasadamOrder first (persisted), then create each
        PrasadamOrderItem with the correct order_id FK, add each to the
        session, then commit.
        """
        total_amount = 0.0
        validated_items = []

        # Validate all items BEFORE creating any DB records
        for item_req in req.items:
            item = await self.repo.get_prasadam_item_by_id(temple_id, item_req.item_id)
            if not item:
                raise NotFoundException(f"Prasadam item {item_req.item_id} not found")
            if not item.is_available:
                raise BadRequestException(f"'{item.name}' is currently not available")
            subtotal      = float(item.price or 0) * item_req.quantity
            total_amount += subtotal
            validated_items.append((item, item_req.quantity, subtotal))

        # Create the master order first to get its id
        order = PrasadamOrder(
            temple_id    = temple_id,
            user_id      = user_id,
            total_amount = total_amount,
            pickup_date  = req.pickup_date,
            status       = "PENDING",
        )
        self.db.add(order)
        await self.db.flush()       # writes order to DB and populates order.id

        # Create order items with the proper FK
        for item, quantity, subtotal in validated_items:
            order_item = PrasadamOrderItem(
                order_id   = order.id,
                item_id    = item.id,
                quantity   = quantity,
                unit_price = float(item.price or 0),
                subtotal   = subtotal,
            )
            self.db.add(order_item)

        await self.db.commit()

        # Re-fetch with eager-loaded items for the response
        created = await self.repo.create_prasadam_order.__func__(
            self.repo, order
        ) if False else await self._reload_order(order.id)

        logger.info(
            "PrasadamOrder created order_id=%s temple=%s user=%s total=%.2f",
            order.id, temple_id, user_id, total_amount,
        )
        return PrasadamOrderResponse.model_validate(created)

    async def _reload_order(self, order_id) -> PrasadamOrder:
        """Reload PrasadamOrder with items eager-loaded after commit."""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        result = await self.db.execute(
            select(PrasadamOrder)
            .options(selectinload(PrasadamOrder.items))
            .where(PrasadamOrder.id == order_id)
        )
        return result.scalar_one()

    # ── My Prasadam Orders ────────────────────────────────────────────────────

    async def get_my_prasadam_orders(self, temple_id: UUID, user_id: UUID):
        orders = await self.repo.get_prasadam_orders_by_user(temple_id, user_id)
        return [PrasadamOrderResponse.model_validate(o) for o in orders]


        #pooja services#
    async def bulk_generate_pooja_slots(
        self, temple_id: UUID, service_id: UUID, req: PoojaSlotBulkGenerate
        ):
            from datetime import timedelta

            service = await self.repo.get_pooja_service_by_id(temple_id, service_id)
            if not service:
                raise NotFoundException("Pooja service not found")

            slots = []
            current_date = req.from_date
            while current_date <= req.to_date:
                slot = PoojaSlot(
                    temple_id        = temple_id,
                    pooja_service_id = service_id,
                    slot_date        = current_date,
                    start_time       = req.start_time,
                    end_time         = req.end_time,
                    total_quota      = req.total_quota,
                    booked_count     = 0,
                    is_active        = True,
                )
                self.db.add(slot)
                slots.append(slot)
                current_date += timedelta(days=1)

            await self.db.commit()   # ← OUTSIDE loop
            return {                 # ← OUTSIDE loop
            "generated_count": len(slots),
            "message": f"{len(slots)} pooja slots generated successfully"
            }



    #prasadam#
    async def create_prasadam_item(self, temple_id: UUID, req: PrasadamItemCreate):
            item = PrasadamItem(
                temple_id=temple_id,
                name=req.name,
                description=req.description,
                price=req.price,
                is_available=req.is_available
            )

            self.db.add(item)
            await self.db.commit()
            await self.db.refresh(item)
            return PrasadamItemResponse.model_validate(item)