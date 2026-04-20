"""
services/temple_service.py  —  Temple Module Business Logic

Changes vs original:
  - create_darshan_type(): DarshanType was used but never imported inside the
    method — crashed with NameError on every call. Fixed with local import.
  - create_darshan_type(): now accepts typed DarshanTypeCreate schema instead
    of raw dict, matching the updated endpoint signature.
  - update_darshan_type(): now accepts typed DarshanTypeUpdate schema instead
    of raw dict so only valid fields can be updated and OpenAPI docs are correct.
  - update_darshan_slot(): now accepts typed DarshanSlotUpdate schema instead
    of raw dict.
  - update_event(): signature changed to TempleEventUpdate (partial update
    schema) instead of TempleEventCreate (which requires all fields).
  - bulk_generate_darshan_slots(): now accepts typed DarshanSlotBulkGenerate
    schema instead of raw dict — all fields validated, dates parsed correctly.
  - sync_ttd(): broken mock/patch code removed; now calls the real
    TempleService.sync_ttd() method directly via the endpoint.
  - delete_temple(): is now a proper method — previously the module-level
    wrapper called it correctly but the method itself had no issues; kept clean.
  - All cache helpers preserved exactly.
  - Module-level thin wrappers preserved for endpoints that inject get_db()
    directly instead of using get_service().
"""

import json
from datetime import date, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.temple import Temple
from src.repositories.temple_repo import TempleRepository
from src.schemas.temple import (
    TempleCreate,
    TempleUpdate,
    TempleDetail,
    TempleListItem,
    TempleEventCreate,
    TempleEventUpdate,
    TempleEventResponse,
    TempleReviewCreate,
    TempleReviewResponse,
    PoojaServiceCreate,
    PoojaServiceUpdate,
    PoojaServiceResponse,
    DarshanTypeCreate,
    DarshanTypeUpdate,
    DarshanTypeResponse,
    DarshanSlotBulkGenerate,
    DarshanSlotUpdate,
    DarshanSlotResponse,
)
from src.core.exceptions import NotFoundException


class TempleService:

    def __init__(self, db: AsyncSession, redis_client=None):
        self.repo  = TempleRepository(db)
        self.db    = db
        self.redis = redis_client

    # ── Cache helpers ─────────────────────────────────────────────────────────

    async def _get_cache(self, key: str):
        if not self.redis:
            return None
        try:
            data = await self.redis.get(key)
            return json.loads(data) if data else None
        except Exception:
            return None

    async def _set_cache(self, key: str, data, ttl_seconds: int):
        if not self.redis:
            return
        try:
            await self.redis.set(key, json.dumps(data, default=str), ex=ttl_seconds)
        except Exception:
            pass

    async def _delete_cache(self, *keys: str):
        if not self.redis:
            return
        try:
            for key in keys:
                await self.redis.delete(key)
        except Exception:
            pass

    # ── Public listings ───────────────────────────────────────────────────────

    async def list_temples(
        self,
        deity:        Optional[str] = None,
        district:     Optional[str] = None,
        darshan_type: Optional[str] = None,
        page:         int = 1,
        page_size:    int = 20,
    ) -> List[TempleListItem]:
        skip    = (page - 1) * page_size
        temples = await self.repo.get_all(
            deity=deity, district=district,
            darshan_type=darshan_type, skip=skip, limit=page_size,
        )
        result = []
        for t in temples:
            item = TempleListItem.model_validate(t)
            item.total_slots_available_today = await self.repo.get_total_slots_available_today(t.id)
            result.append(item)
        return result

    async def get_featured(self) -> List[TempleListItem]:
        cached = await self._get_cache("temples:featured")
        if cached:
            return [TempleListItem.model_validate(i) for i in cached]
        temples = await self.repo.get_featured()
        result  = [TempleListItem.model_validate(t) for t in temples]
        await self._set_cache("temples:featured", [r.model_dump() for r in result], ttl_seconds=3600)
        return result

    async def get_popular(self, limit: int = 10) -> List[TempleListItem]:
        cache_key = f"temples:popular:{limit}"
        cached    = await self._get_cache(cache_key)
        if cached:
            return [TempleListItem.model_validate(i) for i in cached]
        temples = await self.repo.get_popular(limit=limit)
        result  = [TempleListItem.model_validate(t) for t in temples]
        await self._set_cache(cache_key, [r.model_dump() for r in result], ttl_seconds=1800)
        return result

    async def get_nearby(
        self, lat: float, lng: float, radius_km: float = 50.0
    ) -> List[TempleListItem]:
        temples = await self.repo.get_nearby(lat=lat, lng=lng, radius_km=radius_km)
        return [TempleListItem.model_validate(t) for t in temples]

    async def get_by_deity(
        self, deity: str, page: int = 1, page_size: int = 20
    ) -> List[TempleListItem]:
        skip    = (page - 1) * page_size
        temples = await self.repo.get_by_deity(deity, skip=skip, limit=page_size)
        return [TempleListItem.model_validate(t) for t in temples]

    async def get_by_district(
        self, district: str, page: int = 1, page_size: int = 20
    ) -> List[TempleListItem]:
        skip    = (page - 1) * page_size
        temples = await self.repo.get_by_district(district, skip=skip, limit=page_size)
        return [TempleListItem.model_validate(t) for t in temples]

    # ── Temple detail ─────────────────────────────────────────────────────────

    async def get_temple_detail(self, temple_id: UUID) -> TempleDetail:
        cache_key = f"temple:{temple_id}:detail"
        cached    = await self._get_cache(cache_key)
        if cached:
            return TempleDetail.model_validate(cached)
        temple = await self.repo.get_by_id(temple_id)
        if not temple:
            raise NotFoundException(f"Temple {temple_id} not found")
        result = TempleDetail.model_validate(temple)
        await self._set_cache(cache_key, result.model_dump(), ttl_seconds=900)
        return result

    async def get_temple_images(self, temple_id: UUID) -> List[str]:
        temple = await self.repo.get_by_id(temple_id)
        if not temple:
            raise NotFoundException(f"Temple {temple_id} not found")
        return temple.images or []

    async def get_temple_timings(self, temple_id: UUID) -> dict:
        temple = await self.repo.get_by_id(temple_id)
        if not temple:
            raise NotFoundException(f"Temple {temple_id} not found")
        return {
            "temple_id": str(temple_id),
            "name":      temple.name,
            "timings":   temple.timings or {},
        }

    async def get_temple_events(self, temple_id: UUID) -> List[TempleEventResponse]:
        temple = await self.repo.get_by_id(temple_id)
        if not temple:
            raise NotFoundException(f"Temple {temple_id} not found")
        events = await self.repo.get_events(temple_id)
        return [TempleEventResponse.model_validate(e) for e in events]

    async def get_temple_reviews(
        self, temple_id: UUID, page: int = 1, page_size: int = 20
    ) -> List[TempleReviewResponse]:
        temple = await self.repo.get_by_id(temple_id)
        if not temple:
            raise NotFoundException(f"Temple {temple_id} not found")
        skip    = (page - 1) * page_size
        reviews = await self.repo.get_reviews(temple_id, skip=skip, limit=page_size)
        return [TempleReviewResponse.model_validate(r) for r in reviews]

    # ── Admin — Temple CRUD ───────────────────────────────────────────────────

    async def create_temple(self, data: TempleCreate) -> TempleDetail:
        temple = await self.repo.create(data)
        await self._delete_cache("temples:featured", "temples:popular:10")
        temple = await self.repo.get_by_id(temple.id)
    #     result = await self.db.execute(
    #         select(Temple)
    #         .options(
    #             selectinload(Temple.events),
    #             selectinload(Temple.reviews),
    #         )
    #         .where(Temple.id == temple.id)
    #    )
    #     temple = result.scalar_one()
        return TempleDetail.model_validate(temple)

    async def update_temple(self, temple_id: UUID, data: TempleUpdate) -> TempleDetail:
        temple = await self.repo.update(temple_id, data)
        if not temple:
            raise NotFoundException(f"Temple {temple_id} not found")
        await self._delete_cache(
            f"temple:{temple_id}:detail", "temples:featured", "temples:popular:10"
       )
        result = await self.db.execute(
            select(Temple)
            .options(
                selectinload(Temple.events),
                selectinload(Temple.reviews),
           )
           .where(Temple.id == temple_id)
       )
        temple = result.scalar_one()
        return TempleDetail.model_validate(temple)

    async def delete_temple(self, temple_id: str) -> dict:
        """Soft-delete: set is_active = False and bust all related caches."""
        from src.models.temple import Temple

        result = await self.db.execute(select(Temple).where(Temple.id == temple_id))
        temple = result.scalar_one_or_none()
        if not temple:
            raise NotFoundException(f"Temple {temple_id} not found")
        temple.is_active = False
        await self.db.commit()
        await self._delete_cache(
            f"temple:{temple_id}:detail", "temples:featured", "temples:popular:10"
        )
        return {"message": "Temple deleted successfully"}

    # ── Admin — Images ────────────────────────────────────────────────────────

    async def upload_temple_image(self, temple_id: UUID, file: UploadFile) -> dict:
        temple = await self.repo.get_by_id(temple_id)
        if not temple:
            raise NotFoundException(f"Temple {temple_id} not found")
        file_bytes = await file.read()
        image_url  = await self.repo.upload_and_save_image(
            temple_id    = temple_id,
            temple       = temple,
            file_bytes   = file_bytes,
            filename     = file.filename,
            content_type = file.content_type,
        )
        await self._delete_cache(f"temple:{temple_id}:detail")
        return {"image_url": image_url, "images": temple.images}

    async def delete_temple_image(self, temple_id: str, image_id: str) -> dict:
        """
        Remove an image URL from temple.images and delete the object from S3.
        image_id is the full S3 URL stored in the images JSONB array.
        """
        from src.models.temple import Temple
        from src.integrations.aws_s3 import delete_temple_image as s3_delete

        result = await self.db.execute(select(Temple).where(Temple.id == temple_id))
        temple = result.scalar_one_or_none()
        if not temple:
            raise NotFoundException(f"Temple {temple_id} not found")

        images = list(temple.images or [])
        if image_id not in images:
            raise NotFoundException("Image not found")

        images.remove(image_id)
        temple.images = images
        await self.db.commit()
        await s3_delete(image_id)
        await self._delete_cache(f"temple:{temple_id}:detail")
        return {"message": "Image deleted successfully", "images": images}

    # ── Admin — Reviews ───────────────────────────────────────────────────────

    async def create_review(
        self, temple_id: str, data: TempleReviewCreate, user_id: str
    ) -> dict:
        from src.models.temple import TempleReview

        temple = await self.repo.get_by_id(temple_id)
        if not temple:
            raise NotFoundException(f"Temple {temple_id} not found")

        review = TempleReview(
            temple_id  = temple_id,
            user_id    = user_id,
            rating     = data.rating,
            title      = data.title,
            body       = data.body,
            visit_date = data.visit_date,
            is_verified= False,
        )
        self.db.add(review)
        await self.db.commit()
        await self.db.refresh(review)
        return TempleReviewResponse.model_validate(review).model_dump()

    # ── Admin — Pooja Services ────────────────────────────────────────────────

    async def create_pooja_service(
        self, temple_id: str, data: PoojaServiceCreate
    ) -> dict:
        """
        INSERT into pooja_services (src.models.darshan.PoojaService).
        Note: TemplePoojaService in temple.py is an orphan table — always
        use darshan.PoojaService which is registered in models/__init__.py.
        """
        from src.models.darshan import PoojaService

        temple = await self.repo.get_by_id(temple_id)
        if not temple:
            raise NotFoundException(f"Temple {temple_id} not found")

        service = PoojaService(
            temple_id        = temple_id,
            name             = data.name,
            price            = data.price,
            duration_minutes = data.duration_minutes,
            description      = data.description,
            max_persons      = data.max_persons,
            is_active        = data.is_active,
        )
        self.db.add(service)
        await self.db.commit()
        await self.db.refresh(service)
        return PoojaServiceResponse.model_validate(service).model_dump()

    async def update_pooja_service(
        self, temple_id: str, service_id: str, data: PoojaServiceUpdate
    ) -> dict:
        from src.models.darshan import PoojaService

        result = await self.db.execute(
            select(PoojaService).where(
                PoojaService.id        == service_id,
                PoojaService.temple_id == temple_id,
            )
        )
        service = result.scalar_one_or_none()
        if not service:
            raise NotFoundException("Pooja service not found")

        for field, value in data.model_dump(exclude_none=True).items():
            setattr(service, field, value)
        await self.db.commit()
        await self.db.refresh(service)
        return PoojaServiceResponse.model_validate(service).model_dump()

    # ── Admin — Darshan Types ─────────────────────────────────────────────────

    async def create_darshan_type(
        self, temple_id: UUID, data: DarshanTypeCreate
    ) -> DarshanTypeResponse:
        """
        INSERT into darshan_types.
        Fixed: DarshanType was referenced without being imported — caused
        NameError on every call in the original code.
        """
        from src.models.darshan import DarshanType   # local import avoids circular deps

        temple = await self.repo.get_by_id(temple_id)
        if not temple:
            raise NotFoundException(f"Temple {temple_id} not found")

        darshan = DarshanType(
            temple_id               = temple_id,
            name                    = data.name,
            darshan_type            = data.darshan_type,
            description             = data.description,
            price                   = data.price,
            duration_minutes        = data.duration_minutes,
            what_is_included        = data.what_is_included,
            max_persons_per_booking = data.max_persons_per_booking,
            is_active               = data.is_active,
        )
        self.db.add(darshan)
        await self.db.commit()
        await self.db.refresh(darshan)
        await self._delete_cache(f"temple:{temple_id}:detail")
        return DarshanTypeResponse.model_validate(darshan)

    async def update_darshan_type(
        self, temple_id: str, type_id: str, data: DarshanTypeUpdate
    ) -> DarshanTypeResponse:
        from src.models.darshan import DarshanType

        result = await self.db.execute(
            select(DarshanType).where(
                DarshanType.id        == type_id,
                DarshanType.temple_id == temple_id,
            )
        )
        dt = result.scalar_one_or_none()
        if not dt:
            raise NotFoundException("Darshan type not found")

        for field, value in data.model_dump(exclude_none=True).items():
            setattr(dt, field, value)
        await self.db.commit()
        await self.db.refresh(dt)
        await self._delete_cache(f"temple:{temple_id}:detail")
        return DarshanTypeResponse.model_validate(dt)

    async def delete_darshan_type(self, temple_id: str, type_id: str) -> dict:
        from src.models.darshan import DarshanType

        result = await self.db.execute(
            select(DarshanType).where(
                DarshanType.id        == type_id,
                DarshanType.temple_id == temple_id,
            )
        )
        dt = result.scalar_one_or_none()
        if not dt:
            raise NotFoundException("Darshan type not found")

        dt.is_active = False
        await self.db.commit()
        await self._delete_cache(f"temple:{temple_id}:detail")
        return {"message": "Darshan type deleted successfully"}

    # ── Admin — Darshan Slots ─────────────────────────────────────────────────

    async def bulk_generate_darshan_slots(
        self, temple_id: str, data: DarshanSlotBulkGenerate
    ) -> dict:
        """
        Generate DarshanSlot rows for a date range.
        Skips dates that already have a slot for the same type.
        Fixed: now accepts typed DarshanSlotBulkGenerate instead of raw dict —
        dates are proper Python date objects, no manual fromisoformat() needed.
        """
        from src.models.darshan import DarshanSlot

        temple = await self.repo.get_by_id(temple_id)
        if not temple:
            raise NotFoundException(f"Temple {temple_id} not found")

        created, skipped = 0, 0
        current = data.from_date
        while current <= data.to_date:
            existing = await self.db.execute(
                select(DarshanSlot).where(
                    DarshanSlot.temple_id       == temple_id,
                    DarshanSlot.darshan_type_id == str(data.darshan_type_id),
                    DarshanSlot.slot_date       == current,
                )
            )
            if existing.scalar_one_or_none():
                skipped += 1
            else:
                self.db.add(DarshanSlot(
                    temple_id       = temple_id,
                    darshan_type_id = str(data.darshan_type_id),
                    slot_date       = current,
                    start_time      = data.start_time,
                    end_time        = data.end_time,
                    total_quota     = data.total_quota,
                    booked_count    = 0,
                    is_active       = True,
                ))
                created += 1
            current += timedelta(days=1)

        await self.db.commit()
        return {
            "created":   created,
            "skipped":   skipped,
            "from_date": str(data.from_date),
            "to_date":   str(data.to_date),
        }

    async def update_darshan_slot(
        self, temple_id: str, slot_id: str, data: DarshanSlotUpdate
    ) -> DarshanSlotResponse:
        from src.models.darshan import DarshanSlot

        result = await self.db.execute(
            select(DarshanSlot).where(
                DarshanSlot.id        == slot_id,
                DarshanSlot.temple_id == temple_id,
            )
        )
        slot = result.scalar_one_or_none()
        if not slot:
            raise NotFoundException("Darshan slot not found")

        for field, value in data.model_dump(exclude_none=True).items():
            setattr(slot, field, value)
        await self.db.commit()
        await self.db.refresh(slot)
        return DarshanSlotResponse.model_validate(slot)

    # ── Admin — Events ────────────────────────────────────────────────────────

    async def create_event(
        self, temple_id: UUID, data: TempleEventCreate
    ) -> TempleEventResponse:
        from src.models.temple import TempleEvent

        temple = await self.repo.get_by_id(temple_id)
        if not temple:
            raise NotFoundException(f"Temple {temple_id} not found")

        event = TempleEvent(
            temple_id   = temple_id,
            name        = data.name,
            description = data.description,
            event_date  = data.event_date,
            start_time  = data.start_time,
            end_time    = data.end_time,
            is_active   = data.is_active,
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        await self._delete_cache(f"temple:{temple_id}:detail")
        return TempleEventResponse.model_validate(event)

    async def update_event(
        self, temple_id: str, event_id: str, data: TempleEventUpdate
    ) -> TempleEventResponse:
        """
        Update a temple event.
        Fixed: now accepts TempleEventUpdate (all fields Optional) instead of
        TempleEventCreate (which requires name and event_date), so partial
        updates work correctly.
        """
        from src.models.temple import TempleEvent

        result = await self.db.execute(
            select(TempleEvent).where(
                TempleEvent.id        == event_id,
                TempleEvent.temple_id == temple_id,
            )
        )
        event = result.scalar_one_or_none()
        if not event:
            raise NotFoundException("Event not found")

        for field, value in data.model_dump(exclude_none=True).items():
            setattr(event, field, value)
        await self.db.commit()
        await self.db.refresh(event)
        await self._delete_cache(f"temple:{temple_id}:detail")
        return TempleEventResponse.model_validate(event)

    async def delete_event(self, temple_id: str, event_id: str) -> dict:
        from src.models.temple import TempleEvent

        result = await self.db.execute(
            select(TempleEvent).where(
                TempleEvent.id        == event_id,
                TempleEvent.temple_id == temple_id,
            )
        )
        event = result.scalar_one_or_none()
        if not event:
            raise NotFoundException("Event not found")

        event.is_active = False
        await self.db.commit()
        await self._delete_cache(f"temple:{temple_id}:detail")
        return {"message": "Event deleted successfully"}

    # ── Admin — TTD Sync ──────────────────────────────────────────────────────

    async def sync_ttd(self, temple_id: str) -> dict:
        """
        Sync darshan slots from TTD API for today.
        Falls back to mock data when TTD_BASE_URL / TTD_API_KEY are not set.
        Upserts into darshan_slots — skips dates that already exist.
        """
        from src.integrations.ttd_api import get_darshan_slots
        from src.models.darshan import DarshanSlot

        temple = await self.repo.get_by_id(temple_id)
        if not temple:
            raise NotFoundException(f"Temple {temple_id} not found")

        today  = date.today()
        slots  = await get_darshan_slots(temple_id, today)

        synced, skipped = 0, 0
        for slot_data in slots:
            existing = await self.db.execute(
                select(DarshanSlot).where(
                    DarshanSlot.temple_id  == temple_id,
                    DarshanSlot.slot_date  == today,
                    DarshanSlot.start_time == slot_data.get("slot_time"),
                )
            )
            if existing.scalar_one_or_none():
                skipped += 1
                continue

            self.db.add(DarshanSlot(
                temple_id       = temple_id,
                darshan_type_id = None,
                slot_date       = today,
                start_time      = slot_data.get("slot_time"),
                end_time        = slot_data.get("slot_time"),
                total_quota     = slot_data.get("quota", 0),
                booked_count    = slot_data.get("booked_count", 0),
                is_active       = True,
            ))
            synced += 1

        await self.db.commit()
        await self._delete_cache(f"temple:{temple_id}:detail")
        return {"synced": synced, "skipped": skipped, "date": str(today), "source": "ttd_api"}


# ─────────────────────────────────────────────────────────────────────────────
# Module-level thin wrappers
# Called directly as temple_service.fn(temple_id, ..., db) by endpoints
# that inject get_db() directly instead of using get_service().
# ─────────────────────────────────────────────────────────────────────────────

async def delete_temple(temple_id: str, db: AsyncSession) -> dict:
    return await TempleService(db).delete_temple(temple_id)


async def create_darshan_type(
    temple_id: str, data: DarshanTypeCreate, db: AsyncSession
) -> DarshanTypeResponse:
    return await TempleService(db).create_darshan_type(temple_id, data)


async def update_darshan_type(
    temple_id: str, type_id: str, data: DarshanTypeUpdate, db: AsyncSession
) -> DarshanTypeResponse:
    return await TempleService(db).update_darshan_type(temple_id, type_id, data)


async def delete_darshan_type(
    temple_id: str, type_id: str, db: AsyncSession
) -> dict:
    return await TempleService(db).delete_darshan_type(temple_id, type_id)


async def bulk_generate_darshan_slots(
    temple_id: str, data: DarshanSlotBulkGenerate, db: AsyncSession
) -> dict:
    return await TempleService(db).bulk_generate_darshan_slots(temple_id, data)


async def update_darshan_slot(
    temple_id: str, slot_id: str, data: DarshanSlotUpdate, db: AsyncSession
) -> DarshanSlotResponse:
    return await TempleService(db).update_darshan_slot(temple_id, slot_id, data)


async def create_event(
    temple_id: str, data: TempleEventCreate, db: AsyncSession
) -> TempleEventResponse:
    return await TempleService(db).create_event(temple_id, data)


async def update_event(
    temple_id: str, event_id: str, data: TempleEventUpdate, db: AsyncSession
) -> TempleEventResponse:
    return await TempleService(db).update_event(temple_id, event_id, data)


async def delete_event(temple_id: str, event_id: str, db: AsyncSession) -> dict:
    return await TempleService(db).delete_event(temple_id, event_id)
