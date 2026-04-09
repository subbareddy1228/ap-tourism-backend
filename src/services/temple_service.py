import json
from typing import List, Optional
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.temple_repo import TempleRepository
from src.schemas.temple import (
    TempleCreate,
    TempleUpdate,
    TempleDetail,
    TempleListItem,
    TempleEventResponse,
    TempleReviewResponse,
)
from src.models.temple import TemplePoojaService
from src.core.exceptions import NotFoundException


class TempleService:

    def __init__(self, db: AsyncSession, redis_client=None):
        self.repo = TempleRepository(db)
        self.redis = redis_client

    # --------------------------------------------------
    # Cache helpers
    # --------------------------------------------------

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
            await self.redis.set(
                key,
                json.dumps(data, default=str),
                ex=ttl_seconds,
            )
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

    # --------------------------------------------------
    # LIST TEMPLES
    # --------------------------------------------------

    async def list_temples(
        self,
        deity: Optional[str] = None,
        district: Optional[str] = None,
        darshan_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> List[TempleListItem]:

        skip = (page - 1) * page_size

        temples = await self.repo.get_all(
            deity=deity,
            district=district,
            darshan_type=darshan_type,
            skip=skip,
            limit=page_size,
        )

        result = []

        for t in temples:
            item = TempleListItem.model_validate(t)
            item.total_slots_available_today = await self.repo.get_total_slots_available_today(t.id)
            result.append(item)

        return result

    # --------------------------------------------------
    # FEATURED TEMPLES
    # --------------------------------------------------

    async def get_featured(self) -> List[TempleListItem]:

        cache_key = "temples:featured"

        cached = await self._get_cache(cache_key)
        if cached:
            return [TempleListItem.model_validate(item) for item in cached]

        temples = await self.repo.get_featured()
        result = [TempleListItem.model_validate(t) for t in temples]

        await self._set_cache(
            cache_key,
            [r.model_dump() for r in result],
            ttl_seconds=3600,
        )

        return result

    # --------------------------------------------------
    # POPULAR TEMPLES
    # --------------------------------------------------

    async def get_popular(self, limit: int = 10) -> List[TempleListItem]:

        cache_key = f"temples:popular:{limit}"

        cached = await self._get_cache(cache_key)
        if cached:
            return [TempleListItem.model_validate(item) for item in cached]

        temples = await self.repo.get_popular(limit=limit)
        result = [TempleListItem.model_validate(t) for t in temples]

        await self._set_cache(
            cache_key,
            [r.model_dump() for r in result],
            ttl_seconds=1800,
        )

        return result

    # --------------------------------------------------
    # NEARBY TEMPLES
    # --------------------------------------------------

    async def get_nearby(self, lat: float, lng: float, radius_km: float = 50.0) -> List[TempleListItem]:

        temples = await self.repo.get_nearby(lat=lat, lng=lng, radius_km=radius_km)

        return [TempleListItem.model_validate(t) for t in temples]

    # --------------------------------------------------
    # TEMPLE DETAIL
    # --------------------------------------------------

    async def get_temple_detail(self, temple_id: UUID) -> TempleDetail:

        cache_key = f"temple:{temple_id}:detail"

        cached = await self._get_cache(cache_key)
        if cached:
            return TempleDetail.model_validate(cached)

        temple = await self.repo.get_by_id(temple_id)

        if not temple:
            raise NotFoundException(f"Temple {temple_id} not found")

        result = TempleDetail.model_validate(temple)

        await self._set_cache(
            cache_key,
            result.model_dump(),
            ttl_seconds=900,
        )

        return result

    # --------------------------------------------------
    # TEMPLE IMAGES
    # --------------------------------------------------

    async def get_temple_images(self, temple_id: UUID) -> List[str]:

        temple = await self.repo.get_by_id(temple_id)

        if not temple:
            raise NotFoundException(f"Temple {temple_id} not found")

        return temple.images or []

    # --------------------------------------------------
    # TEMPLE EVENTS
    # --------------------------------------------------

    async def get_temple_events(self, temple_id: UUID) -> List[TempleEventResponse]:

        temple = await self.repo.get_by_id(temple_id)

        if not temple:
            raise NotFoundException(f"Temple {temple_id} not found")

        events = await self.repo.get_events(temple_id)

        return [TempleEventResponse.model_validate(e) for e in events]

    # --------------------------------------------------
    # TEMPLE REVIEWS
    # --------------------------------------------------

    async def get_temple_reviews(
        self,
        temple_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> List[TempleReviewResponse]:

        temple = await self.repo.get_by_id(temple_id)

        if not temple:
            raise NotFoundException(f"Temple {temple_id} not found")

        skip = (page - 1) * page_size

        reviews = await self.repo.get_reviews(
            temple_id,
            skip=skip,
            limit=page_size,
        )

        return [TempleReviewResponse.model_validate(r) for r in reviews]
    

        # ─────────────────────────────────────────────
    # CREATE TEMPLE EVENT
    # ─────────────────────────────────────────────

    async def create_event(self, temple_id: UUID, data):

        temple = await self.repo.get_by_id(temple_id)

        if not temple:
            raise NotFoundException(f"Temple {temple_id} not found")

        event = await self.repo.create_event(temple_id, data)

        await self._delete_cache(f"temple:{temple_id}:detail")

        return TempleEventResponse.model_validate(event)    

    # --------------------------------------------------
    # CREATE TEMPLE  (FIXED METHOD)
    # --------------------------------------------------

    async def create_temple(self, data: TempleCreate) -> TempleDetail:

        temple = await self.repo.create(data)

        await self._delete_cache(
            "temples:featured",
            "temples:popular:10",
        )

        temple_dict = temple.__dict__.copy()

        temple_dict.pop("_sa_instance_state", None)

        temple_dict["events"] = []
        temple_dict["reviews"] = []

        return TempleDetail.model_validate(temple_dict)

    # --------------------------------------------------
    # UPDATE TEMPLE
    # --------------------------------------------------

    async def update_temple(self, temple_id: UUID, data: TempleUpdate) -> TempleDetail:

        temple = await self.repo.update(temple_id, data)

        if not temple:
            raise NotFoundException(f"Temple {temple_id} not found")

        await self._delete_cache(
            f"temple:{temple_id}:detail",
            "temples:featured",
            "temples:popular:10",
        )

        return TempleDetail.model_validate(temple, from_attributes=True)

    # --------------------------------------------------
    # UPLOAD TEMPLE IMAGE
    # --------------------------------------------------

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
    
    
    async def get_temple_timings(self, temple_id: UUID):

        temple = await self.repo.get_by_id(temple_id)

        if not temple:
            raise NotFoundException("Temple not found")

        return {
        "temple_id": temple.id,
        "name": temple.name,
        "timings": temple.timings
    }


    # --------------------------------------------------
    # GET TEMPLES BY DEITY
    # --------------------------------------------------

    async def get_by_deity(self, deity: str, page: int = 1, page_size: int = 20):

        skip = (page - 1) * page_size

        temples = await self.repo.get_by_deity(
            deity=deity,
            skip=skip,
            limit=page_size
        )

        return [TempleListItem.model_validate(t) for t in temples]
    

    # --------------------------------------------------
    # CREATE TEMPLE REVIEW
    # --------------------------------------------------

    async def create_review(self, temple_id: UUID, data, user_id: str):

        temple = await self.repo.get_by_id(temple_id)

        if not temple:
            raise NotFoundException(f"Temple {temple_id} not found")

        review = await self.repo.create_review(
            temple_id=temple_id,
            user_id=user_id,
            data=data
        )

        return TempleReviewResponse.model_validate(review)
    

    
# --------------------------------------------------
# CREATE POOJA SERVICE
# --------------------------------------------------

async def create_pooja_service(self, temple_id, data):

    pooja = TemplePoojaService(
        temple_id=temple_id,
        name=data.name,
        price=data.price,
        duration_minutes=data.duration_minutes,
        description=data.description
    )

    self.db.add(pooja)
    await self.db.commit()
    await self.db.refresh(pooja)

    return pooja
    
    