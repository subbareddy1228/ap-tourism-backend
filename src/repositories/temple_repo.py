"""
repositories/temple_repo.py  —  Temple Module Data Access Layer

Changes vs original:
  - Removed incorrect/unused imports:
      `from ast import stmt`, `from asyncio import wait`,
      `from celery import result`, `from src.schemas import review`
  - Removed `TemplePoojaService` import — the service layer correctly
    uses `darshan.PoojaService`; `TemplePoojaService` is an orphan table.
  - Fixed `create_pooja_service()` — was defined OUTSIDE the class body
    (no `self` context), making it a module-level function that would
    crash with NameError on every call.
  - Removed duplicate `get_by_deity()` method (was defined twice).
  - All existing query logic preserved exactly.
"""

from datetime import date
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.temple import Temple, TempleEvent, TempleReview
from src.schemas.temple import TempleCreate, TempleUpdate


class TempleRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    # ─────────────────────────────────────────────────────────────────────────
    # GET / — list with optional filters
    # ─────────────────────────────────────────────────────────────────────────

    async def get_all(
        self,
        deity:        Optional[str] = None,
        district:     Optional[str] = None,
        darshan_type: Optional[str] = None,
        skip:         int = 0,
        limit:        int = 20,
    ) -> List[Temple]:
        query = select(Temple).where(Temple.is_active == True)

        if deity:
            query = query.where(Temple.deity.ilike(f"%{deity}%"))
        if district:
            query = query.where(Temple.district.ilike(f"%{district}%"))
        if darshan_type:
            from src.models.darshan import DarshanType
            query = (
                query
                .join(DarshanType, DarshanType.temple_id == Temple.id)
                .where(
                    DarshanType.darshan_type == darshan_type,
                    DarshanType.is_active    == True,
                )
                .distinct()
            )

        query  = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def count_all(
        self,
        deity:        Optional[str] = None,
        district:     Optional[str] = None,
        darshan_type: Optional[str] = None,
    ) -> int:
        query = (
            select(func.count())
            .select_from(Temple)
            .where(Temple.is_active == True)
        )
        if deity:
            query = query.where(Temple.deity.ilike(f"%{deity}%"))
        if district:
            query = query.where(Temple.district.ilike(f"%{district}%"))
        if darshan_type:
            from src.models.darshan import DarshanType
            subq = (
                select(Temple.id)
                .join(DarshanType, DarshanType.temple_id == Temple.id)
                .where(
                    DarshanType.darshan_type == darshan_type,
                    DarshanType.is_active    == True,
                    Temple.is_active         == True,
                )
                .distinct()
                .subquery()
            )
            query = select(func.count()).select_from(subq)

        result = await self.db.execute(query)
        return result.scalar() or 0

    # ─────────────────────────────────────────────────────────────────────────
    # GET /{id} — eagerly load relationships to avoid MissingGreenlet error
    # In async SQLAlchemy, lazy loading relationships outside the async
    # context raises MissingGreenlet.  selectinload fetches them eagerly
    # in the same session round-trip.
    # ─────────────────────────────────────────────────────────────────────────

    async def get_by_id(self, temple_id: UUID) -> Optional[Temple]:
        result = await self.db.execute(
            select(Temple)
            .options(
                selectinload(Temple.events),
                selectinload(Temple.reviews),
            )
            .where(Temple.id == temple_id, Temple.is_active == True)
        )
        return result.scalar_one_or_none()

    # ─────────────────────────────────────────────────────────────────────────
    # GET /featured
    # ─────────────────────────────────────────────────────────────────────────

    async def get_featured(self, limit: int = 10) -> List[Temple]:
        result = await self.db.execute(
            select(Temple)
            .where(Temple.is_featured == True, Temple.is_active == True)
            .limit(limit)
        )
        return result.scalars().all()

    # ─────────────────────────────────────────────────────────────────────────
    # GET /popular — sorted by booking_count descending
    # ─────────────────────────────────────────────────────────────────────────

    async def get_popular(self, limit: int = 10) -> List[Temple]:
        result = await self.db.execute(
            select(Temple)
            .where(Temple.is_active == True)
            .order_by(Temple.booking_count.desc())
            .limit(limit)
        )
        return result.scalars().all()

    # ─────────────────────────────────────────────────────────────────────────
    # GET /nearby — Haversine formula in SQL
    # func.least(1.0) prevents acos domain error when distance ~ 0
    # ─────────────────────────────────────────────────────────────────────────

    async def get_nearby(
        self,
        lat:       float,
        lng:       float,
        radius_km: float = 50.0,
        limit:     int   = 20,
    ) -> List[Temple]:
        distance_expr = (
            6371 * func.acos(
                func.least(1.0,
                    func.cos(func.radians(lat))
                    * func.cos(func.radians(Temple.latitude))
                    * func.cos(func.radians(Temple.longitude) - func.radians(lng))
                    + func.sin(func.radians(lat))
                    * func.sin(func.radians(Temple.latitude))
                )
            )
        )
        result = await self.db.execute(
            select(Temple)
            .where(
                Temple.is_active     == True,
                Temple.latitude.isnot(None),
                Temple.longitude.isnot(None),
                distance_expr        <= radius_km,
            )
            .order_by(distance_expr)
            .limit(limit)
        )
        return result.scalars().all()

    # ─────────────────────────────────────────────────────────────────────────
    # GET /by-deity/{deity}
    # ─────────────────────────────────────────────────────────────────────────

    async def get_by_deity(
        self, deity: str, skip: int = 0, limit: int = 20
    ) -> List[Temple]:
        result = await self.db.execute(
            select(Temple)
            .where(Temple.deity.ilike(f"%{deity}%"), Temple.is_active == True)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    # ─────────────────────────────────────────────────────────────────────────
    # GET /by-district/{district}
    # ─────────────────────────────────────────────────────────────────────────

    async def get_by_district(
        self, district: str, skip: int = 0, limit: int = 20
    ) -> List[Temple]:
        result = await self.db.execute(
            select(Temple)
            .where(Temple.district.ilike(f"%{district}%"), Temple.is_active == True)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    # ─────────────────────────────────────────────────────────────────────────
    # GET /{id}/events — upcoming only, sorted by date asc
    # ─────────────────────────────────────────────────────────────────────────

    async def get_events(self, temple_id: UUID) -> List[TempleEvent]:
        result = await self.db.execute(
            select(TempleEvent)
            .where(
                TempleEvent.temple_id  == temple_id,
                TempleEvent.event_date >= date.today(),
                TempleEvent.is_active  == True,
            )
            .order_by(TempleEvent.event_date.asc())
        )
        return result.scalars().all()

    # ─────────────────────────────────────────────────────────────────────────
    # GET /{id}/reviews — paginated, newest first
    # ─────────────────────────────────────────────────────────────────────────

    async def get_reviews(
        self, temple_id: UUID, skip: int = 0, limit: int = 20
    ) -> List[TempleReview]:
        result = await self.db.execute(
            select(TempleReview)
            .where(TempleReview.temple_id == temple_id)
            .order_by(TempleReview.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    # ─────────────────────────────────────────────────────────────────────────
    # GET /{id}/images
    # ─────────────────────────────────────────────────────────────────────────

    async def get_images(self, temple_id: UUID) -> list:
        temple = await self.get_by_id(temple_id)
        return temple.images or [] if temple else []

    # ─────────────────────────────────────────────────────────────────────────
    # Slots available today (for TempleListItem.total_slots_available_today)
    # ─────────────────────────────────────────────────────────────────────────

    async def get_total_slots_available_today(self, temple_id: UUID) -> int:
        from src.models.darshan import DarshanSlot
        result = await self.db.execute(
            select(DarshanSlot)
            .where(
                DarshanSlot.temple_id == temple_id,
                DarshanSlot.slot_date == date.today(),
                DarshanSlot.is_active == True,
            )
        )
        slots = result.scalars().all()
        return sum(max(0, s.total_quota - s.booked_count) for s in slots)

    # ─────────────────────────────────────────────────────────────────────────
    # POST / — Admin: create temple
    # ─────────────────────────────────────────────────────────────────────────

    async def create(self, data: TempleCreate) -> Temple:
        temple = Temple(**data.model_dump())
        self.db.add(temple)
        await self.db.commit()
        await self.db.refresh(temple)
        return temple

    # ─────────────────────────────────────────────────────────────────────────
    # PUT /{id} — Admin: partial update
    # ─────────────────────────────────────────────────────────────────────────

    async def update(self, temple_id: UUID, data: TempleUpdate) -> Optional[Temple]:
        temple = await self.get_by_id(temple_id)
        if not temple:
            return None
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(temple, field, value)
        await self.db.commit()
        await self.db.refresh(temple)
        return temple

    # ─────────────────────────────────────────────────────────────────────────
    # POST /{id}/images — upload to S3 and persist URL in temple.images JSONB
    # ─────────────────────────────────────────────────────────────────────────

    async def upload_and_save_image(
        self,
        temple_id:    UUID,
        temple:       Temple,
        file_bytes:   bytes,
        filename:     str,
        content_type: str,
    ) -> str:
        from src.integrations.aws_s3 import upload_temple_image

        image_url = await upload_temple_image(
            file_bytes   = file_bytes,
            content_type = content_type,
            temple_id    = str(temple_id),
            filename     = filename,
        )
        images = list(temple.images or [])
        images.append(image_url)
        temple.images = images
        await self.db.commit()
        return image_url

    # ─────────────────────────────────────────────────────────────────────────
    # POST /{id}/reviews
    # ─────────────────────────────────────────────────────────────────────────

    async def create_review(
        self, temple_id: UUID, user_id: UUID, data
    ) -> TempleReview:
        review = TempleReview(
            temple_id  = temple_id,
            user_id    = user_id,
            rating     = data.rating,
            title      = data.title,
            body       = data.body,
            visit_date = data.visit_date,
        )
        self.db.add(review)
        await self.db.commit()
        await self.db.refresh(review)
        return review

    # ─────────────────────────────────────────────────────────────────────────
    # POST /{id}/events
    # ─────────────────────────────────────────────────────────────────────────

    async def create_event(self, temple_id: UUID, data) -> TempleEvent:
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
        return event

    # ─────────────────────────────────────────────────────────────────────────
    # Increment booking count (called after a booking is confirmed)
    # ─────────────────────────────────────────────────────────────────────────

    async def increment_booking_count(self, temple_id: UUID) -> None:
        temple = await self.get_by_id(temple_id)
        if temple:
            temple.booking_count += 1
            await self.db.commit()
