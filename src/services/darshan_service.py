from datetime import date
from uuid import UUID
 
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
 
from src.models.darshan import (
    DarshanBooking, PoojaBooking, PrasadamOrder, PrasadamOrderItem,
)
from src.repositories.darshan_repo import DarshanRepository
from src.schemas.darshan import (
    DarshanTypeResponse, DarshanSlotResponse,
    DarshanCheckAvailabilityRequest, DarshanCheckAvailabilityResponse,
    DarshanBookRequest, DarshanBookingResponse,
    PoojaServiceResponse, PoojaSlotResponse,
    PoojaBookRequest, PoojaBookingResponse,
    PrasadamItemResponse, PrasadamOrderRequest, PrasadamOrderResponse,
)
 
 
class DarshanService:
 
    async def __init__(self, db: AsyncSession, redis_client=None):
        self.db    = db
        self.redis = redis_client
        self.repo  = DarshanRepository(db)
 
    # ─────────────────────────────────────────────
    # GET /{id}/darshan-types
    # ─────────────────────────────────────────────
    async def get_darshan_types(self, temple_id: UUID):
        types = await self.repo.get_darshan_types(temple_id)
        return [DarshanTypeResponse.model_validate(t) for t in types]
 
    # ─────────────────────────────────────────────
    # GET /{id}/darshan-types/{type_id}
    # ─────────────────────────────────────────────
    async def get_darshan_type_detail(self, temple_id: UUID, type_id: UUID):
        dt = await self.repo.get_darshan_type_by_id(temple_id, type_id)
        if not dt:
            raise HTTPException(status_code=404, detail="Darshan type not found")
        return DarshanTypeResponse.model_validate(dt)
 
    # ─────────────────────────────────────────────
    # GET /{id}/darshan-slots — cached 2 min
    # ─────────────────────────────────────────────
    async def get_darshan_slots(self, temple_id: UUID):
        cache_key = f"darshan_slots:{temple_id}"
        if self.redis:
            try:
                import json
                cached = await self.redis.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception:
                pass
 
        slots  = await self.repo.get_darshan_slots(temple_id)
        result = [DarshanSlotResponse.model_validate(s) for s in slots]
 
        if self.redis:
            try:
                import json
                await self.redis.set(cache_key, json.dumps([r.model_dump() for r in result], default=str), ex=120)
            except Exception:
                pass
 
        return result
 
    # ─────────────────────────────────────────────
    # GET /{id}/darshan-slots/{date}
    # ─────────────────────────────────────────────
    async def get_darshan_slots_by_date(self, temple_id: UUID, slot_date: date):
        slots = await self.repo.get_darshan_slots_by_date(temple_id, slot_date)
        return [DarshanSlotResponse.model_validate(s) for s in slots]
 
    # ─────────────────────────────────────────────
    # POST /{id}/darshan/check-availability
    # ─────────────────────────────────────────────
    async def check_availability(self, temple_id: UUID, req: DarshanCheckAvailabilityRequest):
        slot = await self.repo.get_slot_by_id(req.slot_id)
        if not slot:
            raise HTTPException(status_code=404, detail="Slot not found")
        if slot.temple_id != temple_id:
            raise HTTPException(status_code=400, detail="Slot does not belong to this temple")
 
        is_available = slot.available_count >= req.num_persons
        return DarshanCheckAvailabilityResponse(
            slot_id=req.slot_id,
            is_available=is_available,
            available_count=slot.available_count,
            requested_persons=req.num_persons,
            message="Slots available" if is_available else "Not enough slots available",
        )
 
    # ─────────────────────────────────────────────
    # POST /{id}/darshan/book
    # STEP 1: Lock FIRST
    # STEP 2: Fresh DB read AFTER lock
    # STEP 3: Create PENDING booking
    # STEP 4: Bust cache — lock stays 15 min
    # Team D increments booked_count after payment
    # ─────────────────────────────────────────────
    async def book_darshan(self, temple_id: UUID, user_id: UUID, req: DarshanBookRequest):
 
        # STEP 1 — acquire Redis lock BEFORE DB read
        lock_key = f"slot_lock:{req.slot_id}"
        if self.redis:
            acquired = await self.redis.set(lock_key, str(user_id), nx=True, ex=900)
            if not acquired:
                raise HTTPException(status_code=409, detail="Slot is being booked by another user. Try again.")
 
        # STEP 2 — fresh DB read AFTER lock
        slot = await self.repo.get_slot_by_id(req.slot_id)
        if not slot:
            if self.redis: await self.redis.delete(lock_key)
            raise HTTPException(status_code=404, detail="Slot not found")
 
        if slot.temple_id != temple_id:
            if self.redis: await self.redis.delete(lock_key)
            raise HTTPException(status_code=400, detail="Slot does not belong to this temple")
 
        if slot.available_count < req.num_persons:
            if self.redis: await self.redis.delete(lock_key)
            raise HTTPException(status_code=400, detail=f"Only {slot.available_count} slots available")
 
        # STEP 3 — calculate amount and create PENDING booking
        darshan_type = await self.repo.get_darshan_type_by_id(temple_id, slot.darshan_type_id)
        total_amount = (darshan_type.price if darshan_type else 0.0) * req.num_persons
 
        booking = DarshanBooking(
            temple_id=temple_id,
            slot_id=req.slot_id,
            user_id=user_id,
            num_persons=req.num_persons,
            total_amount=total_amount,
            status="PENDING",
            pilgrim_details=[p.model_dump() for p in req.pilgrim_details] if req.pilgrim_details else [],
        )
        created = await self.repo.create_darshan_booking(booking)
 
        # STEP 4 — bust slot cache only (lock stays alive for 15 min)
        if self.redis:
            try:
                await self.redis.delete(f"darshan_slots:{temple_id}")
            except Exception:
                pass
 
        return DarshanBookingResponse.model_validate(created)
 
    # ─────────────────────────────────────────────
    # GET /{id}/darshan/booking/{booking_id}
    # ─────────────────────────────────────────────
    async def get_darshan_booking(self, temple_id: UUID, booking_id: UUID):
        booking = await self.repo.get_darshan_booking(temple_id, booking_id)
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")
        return DarshanBookingResponse.model_validate(booking)
 
    # ─────────────────────────────────────────────
    # GET /{id}/pooja-services
    # ─────────────────────────────────────────────
    async def get_pooja_services(self, temple_id: UUID):
        services = await self.repo.get_pooja_services(temple_id)
        return [PoojaServiceResponse.model_validate(s) for s in services]
 
    # ─────────────────────────────────────────────
    # GET /{id}/pooja-services/{id}
    # ─────────────────────────────────────────────
    async def get_pooja_service_detail(self, temple_id: UUID, service_id: UUID):
        service = await self.repo.get_pooja_service_by_id(temple_id, service_id)
        if not service:
            raise HTTPException(status_code=404, detail="Pooja service not found")
        return PoojaServiceResponse.model_validate(service)
 
    # ─────────────────────────────────────────────
    # GET /{id}/pooja-services/{id}/slots
    # ─────────────────────────────────────────────
    async def get_pooja_slots(self, temple_id: UUID, service_id: UUID):
        await self.get_pooja_service_detail(temple_id, service_id)
        slots = await self.repo.get_pooja_slots(service_id)
        return [PoojaSlotResponse.model_validate(s) for s in slots]
 
    # ─────────────────────────────────────────────
    # POST /{id}/pooja/book
    # Same lock-first flow as darshan booking
    # ─────────────────────────────────────────────
    async def book_pooja(self, temple_id: UUID, service_id: UUID, user_id: UUID, req: PoojaBookRequest):
        service = await self.repo.get_pooja_service_by_id(temple_id, service_id)
        if not service:
            raise HTTPException(status_code=404, detail="Pooja service not found")
 
        # STEP 1 — acquire lock FIRST
        lock_key = f"pooja_lock:{req.slot_id}"
        if self.redis:
            acquired = await self.redis.set(lock_key, str(user_id), nx=True, ex=900)
            if not acquired:
                raise HTTPException(status_code=409, detail="Slot is being booked by another user. Try again.")
 
        # STEP 2 — fresh read AFTER lock
        slot = await self.repo.get_pooja_slot_by_id(req.slot_id)
        if not slot:
            if self.redis: await self.redis.delete(lock_key)
            raise HTTPException(status_code=404, detail="Pooja slot not found")
 
        if slot.available_count < req.num_persons:
            if self.redis: await self.redis.delete(lock_key)
            raise HTTPException(status_code=400, detail=f"Only {slot.available_count} slots available")
 
        # STEP 3 — create PENDING booking
        booking = PoojaBooking(
            temple_id=temple_id,
            pooja_service_id=service_id,
            slot_id=req.slot_id,
            user_id=user_id,
            num_persons=req.num_persons,
            total_amount=service.price * req.num_persons,
            status="PENDING",
            devotee_name=req.devotee_name,
            gotram=req.gotram,
            special_requests=req.special_requests,
        )
        created = await self.repo.create_pooja_booking(booking)
        return PoojaBookingResponse.model_validate(created)
 
    # ─────────────────────────────────────────────
    # GET /{id}/prasadam
    # ─────────────────────────────────────────────
    async def get_prasadam_items(self, temple_id: UUID):
        items = await self.repo.get_prasadam_items(temple_id)
        return [PrasadamItemResponse.model_validate(i) for i in items]
 
    # ─────────────────────────────────────────────
    # GET /{id}/prasadam/{item_id}
    # ─────────────────────────────────────────────
    async def get_prasadam_item(self, temple_id: UUID, item_id: UUID):
        item = await self.repo.get_prasadam_item_by_id(temple_id, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Prasadam item not found")
        return PrasadamItemResponse.model_validate(item)
 
    # ─────────────────────────────────────────────
    # POST /{id}/prasadam/order
    # ─────────────────────────────────────────────
    async def order_prasadam(self, temple_id: UUID, user_id: UUID, req: PrasadamOrderRequest):
        total_amount = 0.0
        order_items  = []
 
        for item_req in req.items:
            item = await self.repo.get_prasadam_item_by_id(temple_id, item_req.item_id)
            if not item:
                raise HTTPException(status_code=404, detail=f"Prasadam item {item_req.item_id} not found")
            if not item.is_available:
                raise HTTPException(status_code=400, detail=f"{item.name} is currently not available")
            subtotal = item.price * item_req.quantity
            total_amount += subtotal
            order_items.append(PrasadamOrderItem(
                item_id=item_req.item_id,
                quantity=item_req.quantity,
                unit_price=item.price,
                subtotal=subtotal,
            ))
 
        order       = PrasadamOrder(
            temple_id=temple_id,
            user_id=user_id,
            total_amount=total_amount,
            pickup_date=req.pickup_date,
            status="PENDING",
        )
        order.items = order_items
        created     = await self.repo.create_prasadam_order(order)
        return PrasadamOrderResponse.model_validate(created)
 
    # ─────────────────────────────────────────────
    # GET /{id}/prasadam/orders
    # ─────────────────────────────────────────────
    async def get_my_prasadam_orders(self, temple_id: UUID, user_id: UUID):
        orders = await self.repo.get_prasadam_orders_by_user(temple_id, user_id)
        return [PrasadamOrderResponse.model_validate(o) for o in orders]