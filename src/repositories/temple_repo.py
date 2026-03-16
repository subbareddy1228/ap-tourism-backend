from datetime import date
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from src.models.temple import Temple, TempleEvent, TempleReview
from src.schemas.temple import TempleCreate, TempleUpdate


class TempleRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    # ─────────────────────────────────────────────
    # GET / — list with filters
    # ─────────────────────────────────────────────
    async def get_all(
        self,
        deity:        Optional[str] = None,
        district:     Optional[str] = None,
        darshan_type: Optional[str] = None,
        skip:  int = 0,
        limit: int = 20,
    ) -> List[Temple]:
        query = select(Temple).where(Temple.is_active == True)

        if deity:
            query = query.where(Temple.deity.ilike(f"%{deity}%"))
        if district:
            query = query.where(Temple.district.ilike(f"%{district}%"))
        if darshan_type:
            from src.models.darshan import DarshanTypeModel
            query = (
                query
                .join(DarshanTypeModel, DarshanTypeModel.temple_id == Temple.id)
                .where(
                    DarshanTypeModel.darshan_type == darshan_type,
                    DarshanTypeModel.is_active == True,
                )
                .distinct()
            )

        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def count_all(
        self,
        deity:        Optional[str] = None,
        district:     Optional[str] = None,
        darshan_type: Optional[str] = None,
    ) -> int:
        query = select(func.count()).select_from(Temple).where(Temple.is_active == True)
        if deity:
            query = query.where(Temple.deity.ilike(f"%{deity}%"))
        if district:
            query = query.where(Temple.district.ilike(f"%{district}%"))
        if darshan_type:
            from src.models.darshan import DarshanTypeModel
            subq = (
                select(Temple.id)
                .join(DarshanTypeModel, DarshanTypeModel.temple_id == Temple.id)
                .where(
                    DarshanTypeModel.darshan_type == darshan_type,
                    DarshanTypeModel.is_active == True,
                    Temple.is_active == True,
                )
                .distinct()
                .subquery()
            )
            query = select(func.count()).select_from(subq)
        result = await self.db.execute(query)
        return result.scalar() or 0

    # ─────────────────────────────────────────────
    # GET /{id} — eagerly load events and reviews
    #
    # FIX: selectinload prevents MissingGreenlet error.
    # In async SQLAlchemy, relationships are lazy loaded
    # by default. Accessing temple.events or temple.reviews
    # outside async context crashes with MissingGreenlet.
    # selectinload fetches them eagerly in the same session.
    # ─────────────────────────────────────────────
    async def get_by_id(self, temple_id: UUID) -> Optional[Temple]:
        result = await self.db.execute(
            select(Temple)
            .options(
                selectinload(Temple.events),    # eagerly load events
                selectinload(Temple.reviews),   # eagerly load reviews
            )
            .where(Temple.id == temple_id, Temple.is_active == True)
        )
        return result.scalar_one_or_none()

    # ─────────────────────────────────────────────
    # GET /featured
    # ─────────────────────────────────────────────
    async def get_featured(self, limit: int = 10) -> List[Temple]:
        result = await self.db.execute(
            select(Temple)
            .where(Temple.is_featured == True, Temple.is_active == True)
            .limit(limit)
        )
        return result.scalars().all()

    # ─────────────────────────────────────────────
    # GET /popular
    # ─────────────────────────────────────────────
    async def get_popular(self, limit: int = 10) -> List[Temple]:
        result = await self.db.execute(
            select(Temple)
            .where(Temple.is_active == True)
            .order_by(Temple.booking_count.desc())
            .limit(limit)
        )
        return result.scalars().all()

    # ─────────────────────────────────────────────
    # GET /nearby — Haversine in SQL
    # func.least(1.0) prevents acos domain error
    # ─────────────────────────────────────────────
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
                Temple.is_active    == True,
                Temple.latitude.isnot(None),
                Temple.longitude.isnot(None),
                distance_expr <= radius_km,
            )
            .order_by(distance_expr)
            .limit(limit)
        )
        return result.scalars().all()

    # ─────────────────────────────────────────────
    # GET /by-deity/{deity}
    # ─────────────────────────────────────────────
    async def get_by_deity(self, deity: str, skip: int = 0, limit: int = 20) -> List[Temple]:
        result = await self.db.execute(
            select(Temple)
            .where(Temple.deity.ilike(f"%{deity}%"), Temple.is_active == True)
            .offset(skip).limit(limit)
        )
        return result.scalars().all()

    # ─────────────────────────────────────────────
    # GET /by-district/{district}
    # ─────────────────────────────────────────────
    async def get_by_district(self, district: str, skip: int = 0, limit: int = 20) -> List[Temple]:
        result = await self.db.execute(
            select(Temple)
            .where(Temple.district.ilike(f"%{district}%"), Temple.is_active == True)
            .offset(skip).limit(limit)
        )
        return result.scalars().all()

    # ─────────────────────────────────────────────
    # GET /{id}/events — upcoming only
    # ─────────────────────────────────────────────
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

    # ─────────────────────────────────────────────
    # GET /{id}/reviews — paginated, newest first
    # ─────────────────────────────────────────────
    async def get_reviews(self, temple_id: UUID, skip: int = 0, limit: int = 20) -> List[TempleReview]:
        result = await self.db.execute(
            select(TempleReview)
            .where(TempleReview.temple_id == temple_id)
            .order_by(TempleReview.created_at.desc())
            .offset(skip).limit(limit)
        )
        return result.scalars().all()

    # ─────────────────────────────────────────────
    # Total slots available today
    # ─────────────────────────────────────────────
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

    # ─────────────────────────────────────────────
    # POST / — Admin create
    # ─────────────────────────────────────────────
    async def create(self, data: TempleCreate) -> Temple:
        temple = Temple(**data.model_dump())
        self.db.add(temple)
        await self.db.commit()
        await self.db.refresh(temple)
        return temple

    # ─────────────────────────────────────────────
    # PUT /{id} — Admin update
    # ─────────────────────────────────────────────
    async def update(self, temple_id: UUID, data: TempleUpdate) -> Optional[Temple]:
        temple = await self.get_by_id(temple_id)
        if not temple:
            return None
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(temple, field, value)
        await self.db.commit()
        await self.db.refresh(temple)
        return temple

    # ─────────────────────────────────────────────
    # Increment booking count
    # ─────────────────────────────────────────────
    async def increment_booking_count(self, temple_id: UUID) -> None:
        temple = await self.get_by_id(temple_id)
        if temple:
            temple.booking_count += 1
            await self.db.commit()