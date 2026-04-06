import json
 
from typing import List, Optional
 
from uuid import UUID
 
from fastapi import UploadFile
 
from   sqlalchemy.ext.asyncio import AsyncSession
 
from src.repositories.temple_repo import TempleRepository
 
from src.schemas.temple import (
 
    TempleCreate, TempleUpdate, TempleDetail,
 
    TempleListItem, TempleEventResponse, TempleReviewResponse,
 
)
 
from src.core.exceptions import NotFoundException
 
 
class TempleService:
 
    def __init__(self, db: AsyncSession, redis_client=None):
 
        self.repo  = TempleRepository(db)
 
        self.redis = redis_client
 
    # ─────────────────────────────────────────────
 
    # Cache helpers (Redis is sync client — ok to call in async context)
 
    # ─────────────────────────────────────────────
 
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
 
    # ─────────────────────────────────────────────
 
    # GET / — list with filters + total_slots_today
 
    # ─────────────────────────────────────────────
 
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
 
            darshan_type=darshan_type,
 
            skip=skip, limit=page_size,
 
        )
 
        result = []
 
        for t in temples:
 
            item = TempleListItem.model_validate(t)
 
            item.total_slots_available_today = await self.repo.get_total_slots_available_today(t.id)
 
            result.append(item)
 
        return result
 
    # ─────────────────────────────────────────────
 
    # GET /featured — cached 1 hour
 
    # ─────────────────────────────────────────────
 
    async def get_featured(self) -> List[TempleListItem]:
 
        cache_key = "temples:featured"
 
        cached = await self._get_cache(cache_key)
 
        if cached:
 
            return [TempleListItem.model_validate(item) for item in cached]
 
        temples = await self.repo.get_featured()
 
        result  = [TempleListItem.model_validate(t) for t in temples]
 
        await self._set_cache(cache_key, [r.model_dump() for r in result], ttl_seconds=3600)
 
        return result
 
    # ─────────────────────────────────────────────
 
    # GET /popular — cached 30 min
 
    # ─────────────────────────────────────────────
 
    async def get_popular(self, limit: int = 10) -> List[TempleListItem]:
 
        cache_key = f"temples:popular:{limit}"
 
        cached = await self._get_cache(cache_key)
 
        if cached:
 
            return [TempleListItem.model_validate(item) for item in cached]
 
        temples = await self.repo.get_popular(limit=limit)
 
        result  = [TempleListItem.model_validate(t) for t in temples]
 
        await self._set_cache(cache_key, [r.model_dump() for r in result], ttl_seconds=1800)
 
        return result
 
    # ─────────────────────────────────────────────
 
    # GET /nearby
 
    # ─────────────────────────────────────────────
 
    async def get_nearby(self, lat: float, lng: float, radius_km: float = 50.0) -> List[TempleListItem]:
 
        temples = await self.repo.get_nearby(lat=lat, lng=lng, radius_km=radius_km)
 
        return [TempleListItem.model_validate(t) for t in temples]
 
    # ─────────────────────────────────────────────
 
    # GET /by-deity/{deity}
 
    # ─────────────────────────────────────────────
 
    async def get_by_deity(self, deity: str, page: int = 1, page_size: int = 20) -> List[TempleListItem]:
 
        skip    = (page - 1) * page_size
 
        temples = await self.repo.get_by_deity(deity, skip=skip, limit=page_size)
 
        return [TempleListItem.model_validate(t) for t in temples]
 
    # ─────────────────────────────────────────────
 
    # GET /by-district/{district}
 
    # ─────────────────────────────────────────────
 
    async def get_by_district(self, district: str, page: int = 1, page_size: int = 20) -> List[TempleListItem]:
 
        skip    = (page - 1) * page_size
 
        temples = await self.repo.get_by_district(district, skip=skip, limit=page_size)
 
        return [TempleListItem.model_validate(t) for t in temples]
 
    # ─────────────────────────────────────────────
 
    # GET /{id} — cached 15 min
 
    # ─────────────────────────────────────────────
 
    async def get_temple_detail(self, temple_id: UUID) -> TempleDetail:
 
        cache_key = f"temple:{temple_id}:detail"
 
        cached = await self._get_cache(cache_key)
 
        if cached:
 
            return TempleDetail.model_validate(cached)
 
        temple = await self.repo.get_by_id(temple_id)
 
        if not temple:
 
            raise NotFoundException(f"Temple {temple_id} not found")
 
        result = TempleDetail.model_validate(temple)
 
        await self._set_cache(cache_key, result.model_dump(), ttl_seconds=900)
 
        return result
 
    # ─────────────────────────────────────────────
 
    # GET /{id}/images
 
    # ─────────────────────────────────────────────
 
    async def get_temple_images(self, temple_id: UUID) -> List[str]:
 
        temple = await self.repo.get_by_id(temple_id)
 
        if not temple:
 
            raise NotFoundException(f"Temple {temple_id} not found")
 
        return temple.images or []
 
    # ─────────────────────────────────────────────
 
    # GET /{id}/timings
 
    # ─────────────────────────────────────────────
 
    async def get_temple_timings(self, temple_id: UUID):
 
        temple = await self.repo.get_by_id(temple_id)
 
        if not temple:
 
            raise NotFoundException(f"Temple {temple_id} not found")
 
        return {"temple_id": temple_id, "name": temple.name, "timings": temple.timings or {}}
 
    # ─────────────────────────────────────────────
 
    # GET /{id}/events
 
    # ─────────────────────────────────────────────
 
    async def get_temple_events(self, temple_id: UUID) -> List[TempleEventResponse]:
 
        temple = await self.repo.get_by_id(temple_id)
 
        if not temple:
 
            raise NotFoundException(f"Temple {temple_id} not found")
 
        events = await self.repo.get_events(temple_id)
 
        return [TempleEventResponse.model_validate(e) for e in events]
 
    # ─────────────────────────────────────────────
 
    # GET /{id}/reviews
 
    # ─────────────────────────────────────────────
 
    async def get_temple_reviews(self, temple_id: UUID, page: int = 1, page_size: int = 20) -> List[TempleReviewResponse]:
 
        temple = await self.repo.get_by_id(temple_id)
 
        if not temple:
 
            raise NotFoundException(f"Temple {temple_id} not found")
 
        skip    = (page - 1) * page_size
 
        reviews = await self.repo.get_reviews(temple_id, skip=skip, limit=page_size)
 
        return [TempleReviewResponse.model_validate(r) for r in reviews]
 
    # ─────────────────────────────────────────────
 
    # POST / — Admin create
 
    # ─────────────────────────────────────────────
 
    async def create_temple(self, data: TempleCreate) -> TempleDetail:
 
        temple = await self.repo.create(data)
 
        await self._delete_cache("temples:featured", "temples:popular:10")
 
        return TempleDetail.model_validate(temple)
 
    # ─────────────────────────────────────────────
 
    # PUT /{id} — Admin update
 
    # ─────────────────────────────────────────────
 
    async def update_temple(self, temple_id: UUID, data: TempleUpdate) -> TempleDetail:
 
        temple = await self.repo.update(temple_id, data)
 
        if not temple:
 
            raise NotFoundException(f"Temple {temple_id} not found")
 
        await self._delete_cache(f"temple:{temple_id}:detail", "temples:featured", "temples:popular:10")
 
        return TempleDetail.model_validate(temple)
 
    # ─────────────────────────────────────────────
 
    # POST /{id}/images — Admin upload image
    #
    # Reads the uploaded file, delegates to repo for storage
    # and DB persistence, then busts the detail cache so the
    # next GET /{id} reflects the new image list.
    # ─────────────────────────────────────────────
 
    async def upload_temple_image(self, temple_id: UUID, file: UploadFile) -> dict:
 
        temple = await self.repo.get_by_id(temple_id)
 
        if not temple:
 
            raise NotFoundException(f"Temple {temple_id} not found")
 
        file_bytes = await file.read()
 
        image_url = await self.repo.upload_and_save_image(
            temple_id=temple_id,
            temple=temple,
            file_bytes=file_bytes,
            filename=file.filename,
            content_type=file.content_type,
        )
 
        await self._delete_cache(f"temple:{temple_id}:detail")
 
        return {
        "image_url": image_url,
        "images": temple.images,
    }