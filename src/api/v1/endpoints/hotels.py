"""
api/v1/endpoints/hotels.py
Hotel module — all 25 endpoints.

── PUBLIC ────────────────────────────────────────────────────
  GET  /hotels                     List hotels with filters
  GET  /hotels/featured            Featured hotels (cached 1hr)
  GET  /hotels/popular             Popular by booking_count (cached 30min)
  GET  /hotels/nearby              Hotels near lat/lng
  GET  /hotels/{id}                Full hotel detail
  GET  /hotels/{id}/rooms          All room types
  GET  /hotels/{id}/rooms/{room_id} Single room detail
  GET  /hotels/{id}/amenities      Hotel amenities
  GET  /hotels/{id}/images         Hotel images
  GET  /hotels/{id}/reviews        Hotel reviews (paginated)
  GET  /hotels/{id}/availability   Available rooms for date range
  GET  /hotels/{id}/pricing        Room pricing for dates

── PARTNER — HOTEL CRUD ──────────────────────────────────────
  POST   /hotels/partner                        Create hotel
  PUT    /hotels/partner/{id}                   Update hotel
  DELETE /hotels/partner/{id}                   Soft delete hotel

── PARTNER — ROOMS ───────────────────────────────────────────
  POST   /hotels/partner/{id}/rooms             Add room type
  PUT    /hotels/partner/{id}/rooms/{room_id}   Update room
  DELETE /hotels/partner/{id}/rooms/{room_id}   Delete room
  PUT    /hotels/partner/{id}/rooms/{room_id}/pricing     Update price
  PUT    /hotels/partner/{id}/rooms/{room_id}/availability Toggle availability
  POST   /hotels/partner/{id}/rooms/{room_id}/block       Block dates

── PARTNER — MEDIA ───────────────────────────────────────────
  POST   /hotels/partner/{id}/images            Upload images
  DELETE /hotels/partner/{id}/images/{image_id} Delete image
  POST   /hotels/partner/{id}/amenities         Add amenity
  DELETE /hotels/partner/{id}/amenities/{a_id}  Delete amenity
"""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, UploadFile, File, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from src.core.database import get_db
from src.api.deps.auth import get_current_user, get_partner_user
from src.models.user import User
from src.schemas.hotel import (
    HotelCreateRequest, HotelUpdateRequest,
    RoomCreateRequest, RoomUpdateRequest,
    AmenityCreateRequest, AvailabilityRequest,
)
from src.common.responses import APIResponse
from src.services import hotel_service

router = APIRouter(prefix="/hotels", tags=["Hotels"])


# ── Redis (optional — gracefully degrades if Redis is down) ──
def get_redis():
    import redis as redis_lib
    from src.core.config import settings
    client = None
    try:
        client = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
        client.ping()
    except Exception:
        client = None
    return client


# ══════════════════════════════════════════════════════════════
# PUBLIC — BROWSE
# Static routes MUST come before /{id} to avoid conflicts
# ══════════════════════════════════════════════════════════════

@router.get(
    "/featured",
    response_model=APIResponse,
    summary="Featured hotels (cached 1hr)"
)
async def get_featured_hotels(
    db: AsyncSession = Depends(get_db),
):
    """Admin-curated featured hotels. Cached in Redis for 1 hour."""
    redis = get_redis()
    hotels = await hotel_service.get_featured_hotels(db, redis=redis)
    return APIResponse.success(message=f"{len(hotels)} featured hotels", data=hotels)


@router.get(
    "/popular",
    response_model=APIResponse,
    summary="Popular hotels by booking count (cached 30min)"
)
async def get_popular_hotels(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Hotels sorted by booking_count. Cached for 30 minutes."""
    redis = get_redis()
    hotels = await hotel_service.get_popular_hotels(db, limit=limit, redis=redis)
    return APIResponse.success(message=f"{len(hotels)} popular hotels", data=hotels)


@router.get(
    "/nearby",
    response_model=APIResponse,
    summary="Hotels near lat/lng"
)
async def get_nearby_hotels(
    lat:       float = Query(..., description="Latitude"),
    lng:       float = Query(..., description="Longitude"),
    radius_km: float = Query(5.0, ge=0.5, le=100.0, description="Search radius in km"),
    page:      int   = Query(1, ge=1),
    limit:     int   = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Hotels sorted by distance using Haversine formula."""
    hotels = await hotel_service.get_nearby_hotels(
        db, latitude=lat, longitude=lng,
        radius_km=radius_km, page=page, limit=limit
    )
    return APIResponse.success(message=f"{len(hotels)} hotels nearby", data=hotels)


@router.get(
    "",
    response_model=APIResponse,
    summary="List hotels with filters"
)
async def list_hotels(
    city:        Optional[str]   = Query(None, description="Filter by city"),
    checkin:     Optional[str]   = Query(None, description="Check-in date YYYY-MM-DD"),
    checkout:    Optional[str]   = Query(None, description="Check-out date YYYY-MM-DD"),
    guests:      Optional[int]   = Query(None, description="Number of guests"),
    star_rating: Optional[int]   = Query(None, description="Stars: 1-5"),
    hotel_type:  Optional[str]   = Query(None, description="HOTEL | RESORT | HOMESTAY | GUESTHOUSE | DHARAMSHALA"),
    min_price:   Optional[float] = Query(None, description="Min price per night"),
    max_price:   Optional[float] = Query(None, description="Max price per night"),
    page:        int             = Query(1, ge=1),
    limit:       int             = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Browse active hotels. Filters: city, checkin, checkout, guests,
    star_rating, hotel_type, price_range. Sorted by featured first, then rating.
    """
    hotels = await hotel_service.list_hotels(
        db, city=city, star_rating=star_rating, hotel_type=hotel_type,
        min_price=min_price, max_price=max_price,
        checkin=checkin, checkout=checkout, guests=guests,
        page=page, limit=limit
    )
    return APIResponse.success(message=f"{len(hotels)} hotels found", data=hotels)


# ══════════════════════════════════════════════════════════════
# PUBLIC — HOTEL DETAIL
# ══════════════════════════════════════════════════════════════

@router.get(
    "/{hotel_id}/rooms/{room_id}",
    response_model=APIResponse,
    summary="Single room detail"
)
async def get_room_detail(
    hotel_id: str,
    room_id:  str,
    db: AsyncSession = Depends(get_db),
):
    """Single room detail with images, capacity, amenities."""
    data = await hotel_service.get_room_detail(hotel_id, room_id, db)
    return APIResponse.success(message="Room fetched", data=data)


@router.get(
    "/{hotel_id}/rooms",
    response_model=APIResponse,
    summary="All room types for hotel"
)
async def get_hotel_rooms(
    hotel_id: str,
    db: AsyncSession = Depends(get_db),
):
    """All room types for hotel with base prices."""
    data = await hotel_service.get_hotel_rooms(hotel_id, db)
    return APIResponse.success(message=f"{len(data)} rooms found", data=data)


@router.get(
    "/{hotel_id}/amenities",
    response_model=APIResponse,
    summary="Hotel amenities list"
)
async def get_hotel_amenities(
    hotel_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Hotel amenities: pool, wifi, parking, restaurant etc."""
    data = await hotel_service.get_hotel_amenities_public(hotel_id, db)
    return APIResponse.success(message=f"{len(data)} amenities", data=data)


@router.get(
    "/{hotel_id}/images",
    response_model=APIResponse,
    summary="Hotel image URLs"
)
async def get_hotel_images(
    hotel_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Hotel image URLs from S3."""
    data = await hotel_service.get_hotel_images_public(hotel_id, db)
    return APIResponse.success(message=f"{len(data)} images", data=data)


@router.get(
    "/{hotel_id}/reviews",
    response_model=APIResponse,
    summary="Hotel reviews (paginated)"
)
async def get_hotel_reviews(
    hotel_id: str,
    page:     int = Query(1, ge=1),
    limit:    int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Hotel reviews with rating breakdown. Sorted by most helpful."""
    data = await hotel_service.get_hotel_reviews(hotel_id, page=page, limit=limit, db=db)
    return APIResponse.success(message="Reviews fetched", data=data)


@router.get(
    "/{hotel_id}/availability",
    response_model=APIResponse,
    summary="Check available rooms for date range"
)
async def get_hotel_availability(
    hotel_id:  str,
    checkin:   str = Query(..., description="Check-in date YYYY-MM-DD"),
    checkout:  str = Query(..., description="Check-out date YYYY-MM-DD"),
    guests:    int = Query(1, ge=1),
    db: AsyncSession = Depends(get_db),
):
    """
    Available rooms for date range.
    Checks room_bookings table. Cached for 2 minutes.
    """
    from src.schemas.hotel import AvailabilityRequest
    from datetime import date
    try:
        ci = date.fromisoformat(checkin)
        co = date.fromisoformat(checkout)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    if co <= ci:
        raise HTTPException(status_code=400, detail="checkout must be after checkin")

    data_req = AvailabilityRequest(check_in=ci, check_out=co, guests=guests)
    result = await hotel_service.check_availability(hotel_id, data_req, db)
    return APIResponse.success(message="Availability fetched", data=result)


@router.get(
    "/{hotel_id}/pricing",
    response_model=APIResponse,
    summary="Room pricing for dates"
)
async def get_hotel_pricing(
    hotel_id: str,
    checkin:  str = Query(..., description="Check-in date YYYY-MM-DD"),
    checkout: str = Query(..., description="Check-out date YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
):
    """Room pricing for dates including dynamic multiplier from pricing engine."""
    data = await hotel_service.get_hotel_pricing(hotel_id, checkin, checkout, db)
    return APIResponse.success(message="Pricing fetched", data=data)


@router.get(
    "/{hotel_id}",
    response_model=APIResponse,
    summary="Full hotel detail"
)
async def get_hotel_detail(
    hotel_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Full hotel detail — includes rooms, images, amenities.
    Only returns active hotels with status=ACTIVE.
    """
    data = await hotel_service.get_hotel_detail(hotel_id, db)
    return APIResponse.success(message="Hotel fetched", data=data)


# ══════════════════════════════════════════════════════════════
# PARTNER — HOTEL CRUD
# ══════════════════════════════════════════════════════════════

@router.post(
    "/partner",
    response_model=APIResponse,
    status_code=201,
    summary="[Partner] Create hotel listing"
)
async def create_hotel(
    data: HotelCreateRequest,
    current_user: User = Depends(get_partner_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create hotel listing. Partner must be VERIFIED (KYC approved).
    Status starts as PENDING — admin must approve before it goes live.
    """
    hotel = await hotel_service.create_hotel(data, current_user, db)
    return APIResponse.success(message="Hotel created. Awaiting admin approval.", data=hotel)


@router.put(
    "/partner/{hotel_id}",
    response_model=APIResponse,
    summary="[Partner] Update hotel"
)
async def update_hotel(
    hotel_id: str,
    data: HotelUpdateRequest,
    current_user: User = Depends(get_partner_user),
    db: AsyncSession = Depends(get_db),
):
    """Update hotel details. Only owner partner can update. Only provided fields updated."""
    updated = await hotel_service.update_hotel(hotel_id, data, current_user, db)
    return APIResponse.success(message="Hotel updated", data=updated)


@router.delete(
    "/partner/{hotel_id}",
    response_model=APIResponse,
    summary="[Partner] Soft delete hotel"
)
async def delete_hotel(
    hotel_id: str,
    current_user: User = Depends(get_partner_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft delete hotel (deactivate, not hard delete). Hides from public listings."""
    result = await hotel_service.delete_hotel(hotel_id, current_user, db)
    return APIResponse.success(message=result["message"])


# ══════════════════════════════════════════════════════════════
# PARTNER — ROOMS
# ══════════════════════════════════════════════════════════════

@router.post(
    "/partner/{hotel_id}/rooms",
    response_model=APIResponse,
    status_code=201,
    summary="[Partner] Add room type"
)
async def add_room(
    hotel_id: str,
    data: RoomCreateRequest,
    current_user: User = Depends(get_partner_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Add room type: name, capacity, price_per_night, total_rooms, amenities.
    Also updates hotel base_price to the lowest active room price.
    """
    room = await hotel_service.add_room(hotel_id, data, current_user, db)
    return APIResponse.success(message="Room added successfully", data=room)


@router.put(
    "/partner/{hotel_id}/rooms/{room_id}",
    response_model=APIResponse,
    summary="[Partner] Update room"
)
async def update_room(
    hotel_id: str,
    room_id:  str,
    data: RoomUpdateRequest,
    current_user: User = Depends(get_partner_user),
    db: AsyncSession = Depends(get_db),
):
    """Update room details. Only provided fields are updated."""
    room = await hotel_service.update_room(hotel_id, room_id, data, current_user, db)
    return APIResponse.success(message="Room updated", data=room)


@router.delete(
    "/partner/{hotel_id}/rooms/{room_id}",
    response_model=APIResponse,
    summary="[Partner] Delete room type"
)
async def delete_room(
    hotel_id: str,
    room_id:  str,
    current_user: User = Depends(get_partner_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete room type. Also recalculates hotel base_price."""
    result = await hotel_service.delete_room(hotel_id, room_id, current_user, db)
    return APIResponse.success(message=result["message"])


class RoomPricingRequest(BaseModel):
    price_per_night: float
    weekend_price:   Optional[float] = None


@router.put(
    "/partner/{hotel_id}/rooms/{room_id}/pricing",
    response_model=APIResponse,
    summary="[Partner] Update room price"
)
async def update_room_pricing(
    hotel_id: str,
    room_id:  str,
    data: RoomPricingRequest,
    current_user: User = Depends(get_partner_user),
    db: AsyncSession = Depends(get_db),
):
    """Update room price per night and optional weekend price."""
    result = await hotel_service.update_room_pricing(
        hotel_id, room_id, data.price_per_night, data.weekend_price, current_user, db
    )
    return APIResponse.success(message="Room pricing updated", data=result)


@router.put(
    "/partner/{hotel_id}/rooms/{room_id}/availability",
    response_model=APIResponse,
    summary="[Partner] Toggle room availability"
)
async def toggle_room_availability(
    hotel_id: str,
    room_id:  str,
    current_user: User = Depends(get_partner_user),
    db: AsyncSession = Depends(get_db),
):
    """Toggle room is_active status. Inactive rooms hidden from guests."""
    result = await hotel_service.toggle_room_availability(hotel_id, room_id, current_user, db)
    return APIResponse.success(message=result["message"], data=result)


class BlockDatesRequest(BaseModel):
    dates:  List[str]
    reason: Optional[str] = None


@router.post(
    "/partner/{hotel_id}/rooms/{room_id}/block",
    response_model=APIResponse,
    status_code=201,
    summary="[Partner] Block dates for room"
)
async def block_room_dates(
    hotel_id: str,
    room_id:  str,
    data: BlockDatesRequest,
    current_user: User = Depends(get_partner_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Block specific dates for a room (maintenance, renovation).
    Prevents bookings on those dates.
    Format: ['2024-12-25', '2024-12-26']
    """
    result = await hotel_service.block_room_dates(
        hotel_id, room_id, data.dates, data.reason, current_user, db
    )
    return APIResponse.success(message=result["message"], data=result)


# ══════════════════════════════════════════════════════════════
# PARTNER — MEDIA
# ══════════════════════════════════════════════════════════════

@router.post(
    "/partner/{hotel_id}/images",
    response_model=APIResponse,
    status_code=201,
    summary="[Partner] Upload hotel images"
)
async def upload_image(
    hotel_id:   str,
    file:       UploadFile = File(...),
    category:   str  = Query("EXTERIOR", description="EXTERIOR | INTERIOR | ROOM | RESTAURANT | POOL | OTHER"),
    caption:    Optional[str]  = Query(None, description="Image caption"),
    is_primary: bool = Query(False, description="Set as primary/cover image"),
    current_user: User = Depends(get_partner_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload hotel image to S3. Max 20 images, 5MB each.
    Setting is_primary=true clears the previous primary flag.
    """
    image = await hotel_service.upload_image(
        hotel_id, file, category, caption, is_primary, current_user, db
    )
    return APIResponse.success(message="Image uploaded successfully", data=image)


@router.delete(
    "/partner/{hotel_id}/images/{image_id}",
    response_model=APIResponse,
    summary="[Partner] Delete hotel image"
)
async def delete_image(
    hotel_id: str,
    image_id: str,
    current_user: User = Depends(get_partner_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove image from S3 and database."""
    result = await hotel_service.delete_image(hotel_id, image_id, current_user, db)
    return APIResponse.success(message=result["message"])


@router.post(
    "/partner/{hotel_id}/amenities",
    response_model=APIResponse,
    status_code=201,
    summary="[Partner] Add hotel amenity"
)
async def add_amenity(
    hotel_id: str,
    data: AmenityCreateRequest,
    current_user: User = Depends(get_partner_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Add amenity to hotel.
    category: GENERAL | WELLNESS | DINING | TRANSPORT | RELIGIOUS | KIDS
    """
    amenity = await hotel_service.add_amenity(hotel_id, data, current_user, db)
    return APIResponse.success(message="Amenity added", data=amenity)


@router.delete(
    "/partner/{hotel_id}/amenities/{amenity_id}",
    response_model=APIResponse,
    summary="[Partner] Delete hotel amenity"
)
async def delete_amenity(
    hotel_id:    str,
    amenity_id:  str,
    current_user: User = Depends(get_partner_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove amenity from hotel."""
    result = await hotel_service.delete_amenity(hotel_id, amenity_id, current_user, db)
    return APIResponse.success(message=result["message"])