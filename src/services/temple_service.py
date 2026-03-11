import json
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from src.repositories.temple_repo import TempleRepository
from src.schemas.temple import (
    TempleCreate, TempleUpdate, TempleDetail,
    TempleListItem, TempleEventResponse, TempleReviewResponse
)
from src.core.exceptions import NotFoundException


class TempleService:

    def __init__(self, db: Session, redis_client=None):
        self.repo = TempleRepository(db)
        self.redis = redis_client

    # ─────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────

    def _get_cache(self, key: str):
        if not self.redis:
            return None
        data = self.redis.get(key)
        return json.loads(data) if data else None

    def _set_cache(self, key: str, data, ttl_seconds: int):
        if self.redis:
            self.redis.setex(key, ttl_seconds, json.dumps(data, default=str))

    # ─────────────────────────────────────────────
    # Public Endpoints
    # ─────────────────────────────────────────────

    def list_temples(
        self,
        deity: Optional[str] = None,
        district: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> List[TempleListItem]:
        skip = (page - 1) * page_size
        temples = self.repo.get_all(deity=deity, district=district, skip=skip, limit=page_size)
        return [TempleListItem.model_validate(t) for t in temples]

    def get_featured(self) -> List[TempleListItem]:
        cache_key = "temples:featured"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        temples = self.repo.get_featured()
        result = [TempleListItem.model_validate(t) for t in temples]
        self._set_cache(cache_key, [r.model_dump() for r in result], ttl_seconds=3600)  # 1 hour
        return result

    def get_popular(self, limit: int = 10) -> List[TempleListItem]:
        cache_key = f"temples:popular:{limit}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        temples = self.repo.get_popular(limit=limit)
        result = [TempleListItem.model_validate(t) for t in temples]
        self._set_cache(cache_key, [r.model_dump() for r in result], ttl_seconds=1800)  # 30 min
        return result

    def get_nearby(
        self, lat: float, lng: float, radius_km: float = 50.0
    ) -> List[TempleListItem]:
        temples = self.repo.get_nearby(lat=lat, lng=lng, radius_km=radius_km)
        return [TempleListItem.model_validate(t) for t in temples]

    def get_by_deity(self, deity: str, page: int = 1, page_size: int = 20) -> List[TempleListItem]:
        skip = (page - 1) * page_size
        temples = self.repo.get_by_deity(deity, skip=skip, limit=page_size)
        return [TempleListItem.model_validate(t) for t in temples]

    def get_by_district(
        self, district: str, page: int = 1, page_size: int = 20
    ) -> List[TempleListItem]:
        skip = (page - 1) * page_size
        temples = self.repo.get_by_district(district, skip=skip, limit=page_size)
        return [TempleListItem.model_validate(t) for t in temples]

    def get_temple_detail(self, temple_id: UUID) -> TempleDetail:
        cache_key = f"temple:{temple_id}:detail"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        temple = self.repo.get_by_id(temple_id)
        if not temple:
            raise NotFoundException(f"Temple {temple_id} not found")

        result = TempleDetail.model_validate(temple)
        self._set_cache(cache_key, result.model_dump(), ttl_seconds=900)  # 15 min
        return result

    def get_temple_images(self, temple_id: UUID) -> List[str]:
        temple = self.repo.get_by_id(temple_id)
        if not temple:
            raise NotFoundException(f"Temple {temple_id} not found")
        return temple.images or []

    def get_temple_timings(self, temple_id: UUID):
        temple = self.repo.get_by_id(temple_id)
        if not temple:
            raise NotFoundException(f"Temple {temple_id} not found")
        return temple.timings or {}

    def get_temple_events(self, temple_id: UUID) -> List[TempleEventResponse]:
        temple = self.repo.get_by_id(temple_id)
        if not temple:
            raise NotFoundException(f"Temple {temple_id} not found")
        events = self.repo.get_events(temple_id)
        return [TempleEventResponse.model_validate(e) for e in events]

    def get_temple_reviews(
        self, temple_id: UUID, page: int = 1, page_size: int = 20
    ) -> List[TempleReviewResponse]:
        temple = self.repo.get_by_id(temple_id)
        if not temple:
            raise NotFoundException(f"Temple {temple_id} not found")
        skip = (page - 1) * page_size
        reviews = self.repo.get_reviews(temple_id, skip=skip, limit=page_size)
        return [TempleReviewResponse.model_validate(r) for r in reviews]

    # ─────────────────────────────────────────────
    # Admin Operations
    # ─────────────────────────────────────────────

    def create_temple(self, data: TempleCreate) -> TempleDetail:
        temple = self.repo.create(data)
        return TempleDetail.model_validate(temple)

    def update_temple(self, temple_id: UUID, data: TempleUpdate) -> TempleDetail:
        temple = self.repo.update(temple_id, data)
        if not temple:
            raise NotFoundException(f"Temple {temple_id} not found")
        # Invalidate cache
        if self.redis:
            self.redis.delete(f"temple:{temple_id}:detail")
            self.redis.delete("temples:featured")
            self.redis.delete("temples:popular:10")
        return TempleDetail.model_validate(temple)
    


   