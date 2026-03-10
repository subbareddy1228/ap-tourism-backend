from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.models.temple import Temple, TempleEvent, TempleReview   # ← fixed: both live in temple.py
from src.schemas.temple import TempleCreate, TempleUpdate


class TempleRepository:

    def __init__(self, db: Session):
        self.db = db

    # ─────────────────────────────────────────────
    # Read Operations
    # ─────────────────────────────────────────────

    def get_all(
        self,
        deity: Optional[str] = None,
        district: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> List[Temple]:
        query = self.db.query(Temple).filter(Temple.is_active == True)
        if deity:
            query = query.filter(Temple.deity.ilike(f"%{deity}%"))
        if district:
            query = query.filter(Temple.district.ilike(f"%{district}%"))
        return query.offset(skip).limit(limit).all()

    def get_by_id(self, temple_id: UUID) -> Optional[Temple]:
        return self.db.query(Temple).filter(
            Temple.id == temple_id, Temple.is_active == True
        ).first()

    def get_featured(self, limit: int = 10) -> List[Temple]:
        return (
            self.db.query(Temple)
            .filter(Temple.is_featured == True, Temple.is_active == True)
            .limit(limit)
            .all()
        )

    def get_popular(self, limit: int = 10) -> List[Temple]:
        return (
            self.db.query(Temple)
            .filter(Temple.is_active == True)
            .order_by(Temple.booking_count.desc())
            .limit(limit)
            .all()
        )

    def get_nearby(
        self,
        lat: float,
        lng: float,
        radius_km: float = 50.0,
        limit: int = 20,
    ) -> List[Temple]:
        distance_expr = (
            6371
            * func.acos(
                func.cos(func.radians(lat))
                * func.cos(func.radians(Temple.latitude))
                * func.cos(func.radians(Temple.longitude) - func.radians(lng))
                + func.sin(func.radians(lat))
                * func.sin(func.radians(Temple.latitude))
            )
        )
        return (
            self.db.query(Temple)
            .filter(
                Temple.is_active == True,
                Temple.latitude.isnot(None),
                Temple.longitude.isnot(None),
                distance_expr <= radius_km,
            )
            .order_by(distance_expr)
            .limit(limit)
            .all()
        )

    def get_by_deity(self, deity: str, skip: int = 0, limit: int = 20) -> List[Temple]:
        return (
            self.db.query(Temple)
            .filter(Temple.deity.ilike(f"%{deity}%"), Temple.is_active == True)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_district(self, district: str, skip: int = 0, limit: int = 20) -> List[Temple]:
        return (
            self.db.query(Temple)
            .filter(Temple.district.ilike(f"%{district}%"), Temple.is_active == True)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_images(self, temple_id: UUID) -> List[str]:
        temple = self.get_by_id(temple_id)
        if not temple:
            return []
        return temple.images or []

    def get_timings(self, temple_id: UUID):
        temple = self.get_by_id(temple_id)
        if not temple:
            return None
        return temple.timings

    def get_events(self, temple_id: UUID) -> List[TempleEvent]:
        return (
            self.db.query(TempleEvent)
            .filter(TempleEvent.temple_id == temple_id, TempleEvent.is_active == True)
            .order_by(TempleEvent.event_date)
            .all()
        )

    def get_reviews(
        self, temple_id: UUID, skip: int = 0, limit: int = 20
    ) -> List[TempleReview]:
        return (
            self.db.query(TempleReview)
            .filter(TempleReview.temple_id == temple_id)
            .order_by(TempleReview.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def add_review(self, temple_id: UUID, user_id: UUID, data: dict) -> TempleReview:
        review = TempleReview(temple_id=temple_id, user_id=user_id, **data)
        self.db.add(review)
        self.db.commit()
        self.db.refresh(review)
        return review

    # ─────────────────────────────────────────────
    # Admin Write Operations
    # ─────────────────────────────────────────────

    def create(self, data: TempleCreate) -> Temple:
        temple = Temple(**data.model_dump())
        self.db.add(temple)
        self.db.commit()
        self.db.refresh(temple)
        return temple

    def update(self, temple_id: UUID, data: TempleUpdate) -> Optional[Temple]:
        temple = self.get_by_id(temple_id)
        if not temple:
            return None
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(temple, field, value)
        self.db.commit()
        self.db.refresh(temple)
        return temple

    def increment_booking_count(self, temple_id: UUID) -> None:
        self.db.query(Temple).filter(Temple.id == temple_id).update(
            {Temple.booking_count: Temple.booking_count + 1}
        )
        self.db.commit()