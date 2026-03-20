"""
api/v1/endpoints/hotels.py
Hotel module — all 25 endpoints split into Public and Partner sections.
 
── PUBLIC (M5-Public — Vamsi Didhikunta LEV147) ──────────────
  GET  /hotels                     List hotels with filters
  GET  /hotels/{id}                Hotel detail
  POST /hotels/{id}/availability   Check room availability
  GET  /hotels/nearby              Find hotels near coordinates
 
── PARTNER (M5-Partner — Ragu Anusha LEV152) ─────────────────
  POST   /hotels/partner                        Create hotel
  GET    /hotels/partner/my-hotels              My hotels list
  GET    /hotels/partner/{id}                   My hotel detail
  PUT    /hotels/partner/{id}                   Update hotel
  DELETE /hotels/partner/{id}                   Delete hotel
  PUT    /hotels/partner/{id}/toggle-status     Activate / deactivate
 
  POST   /hotels/partner/{id}/rooms             Add room
  PUT    /hotels/partner/{id}/rooms/{room_id}   Update room
  DELETE /hotels/partner/{id}/rooms/{room_id}   Delete room
 
  POST   /hotels/partner/{id}/images            Upload image
  DELETE /hotels/partner/{id}/images/{img_id}   Delete image
 
  GET    /hotels/partner/{id}/amenities         List amenities
  POST   /hotels/partner/{id}/amenities         Add amenity
  DELETE /hotels/partner/{id}/amenities/{a_id}  Delete amenity
"""
 
from fastapi import APIRouter, Depends, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
 
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
 
 
# ══════════════════ PUBLIC ENDPOINTS ══════════════════
 
@router.get("", response_model=APIResponse, summary="List all hotels with filters")
async def list_hotels(
    city:        Optional[str] = Query(None, description="Filter by city name"),
    star_rating: Optional[int] = Query(None, description="Filter by stars: 1-5"),
    hotel_type:  Optional[str] = Query(None, description="HOTEL | RESORT | HOMESTAY | GUESTHOUSE | DHARAMSHALA"),
    min_price:   Optional[float] = Query(None, description="Minimum price per night"),
    max_price:   Optional[float] = Query(None, description="Maximum price per night"),
    page:        int = Query(1, ge=1),
    limit:       int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Browse active hotels. Supports filters: city, star_rating, hotel_type, price range.
    Sorted by featured first, then rating.
    """
    hotels = await hotel_service.list_hotels(
        db, city=city, star_rating=star_rating, hotel_type=hotel_type,
        min_price=min_price, max_price=max_price, page=page, limit=limit
    )
    return APIResponse.success(message=f"{len(hotels)} hotels found", data=hotels)
 
 
@router.get("/nearby", response_model=APIResponse, summary="Find hotels near coordinates")
async def get_nearby_hotels(
    latitude:  float = Query(..., description="Latitude of current location"),
    longitude: float = Query(..., description="Longitude of current location"),
    radius_km: float = Query(5.0, description="Search radius in km (default 5)"),
    page:      int = Query(1, ge=1),
    limit:     int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns hotels sorted by distance from given coordinates within the specified radius.
    """
    hotels = await hotel_service.get_nearby_hotels(
        db, latitude=latitude, longitude=longitude,
        radius_km=radius_km, page=page, limit=limit
    )
    return APIResponse.success(message=f"{len(hotels)} hotels nearby", data=hotels)
 
 
@router.get("/{hotel_id}", response_model=APIResponse, summary="Get hotel detail")
async def get_hotel_detail(
    hotel_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Full hotel detail — includes rooms, images, and amenities.
    Only returns active hotels with status=ACTIVE.
    """
    data = await hotel_service.get_hotel_detail(hotel_id, db)
    return APIResponse.success(message="Hotel fetched", data=data)
 
 
@router.post("/{hotel_id}/availability", response_model=APIResponse, summary="Check room availability")
async def check_availability(
    hotel_id: str,
    data: AvailabilityRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Check available rooms for given check_in / check_out / guests.
    Returns list of available room types with pricing.
    """
    result = await hotel_service.check_availability(hotel_id, data, db)
    return APIResponse.success(message="Availability fetched", data=result)
 
 
# ══════════════════ PARTNER ENDPOINTS ══════════════════
 
@router.post("/partner", response_model=APIResponse, status_code=201,
             summary="[Partner] Create hotel listing")
async def create_hotel(
    data: HotelCreateRequest,
    current_user: User = Depends(get_partner_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new hotel listing. Partner must be VERIFIED.
    Status starts as PENDING — admin must approve before it goes live.
    """
    hotel = await hotel_service.create_hotel(data, current_user, db)
    return APIResponse.success(message="Hotel created. Awaiting admin approval.", data=hotel)
 
 
@router.get("/partner/my-hotels", response_model=APIResponse,
            summary="[Partner] List my hotels")
async def get_my_hotels(
    current_user: User = Depends(get_partner_user),
    db: AsyncSession = Depends(get_db),
):
    """All hotel listings owned by the current partner."""
    hotels = await hotel_service.get_my_hotels(current_user, db)
    return APIResponse.success(message=f"{len(hotels)} hotels found", data=hotels)
 
 
@router.get("/partner/{hotel_id}", response_model=APIResponse,
            summary="[Partner] Get my hotel detail")
async def get_my_hotel_detail(
    hotel_id: str,
    current_user: User = Depends(get_partner_user),
    db: AsyncSession = Depends(get_db),
):
    """Full hotel detail for the partner — includes rooms, images, amenities."""
    data = await hotel_service.get_my_hotel_detail(hotel_id, current_user, db)
    return APIResponse.success(message="Hotel fetched", data=data)
 
 
@router.put("/partner/{hotel_id}", response_model=APIResponse,
            summary="[Partner] Update hotel")
async def update_hotel(
    hotel_id: str,
    data: HotelUpdateRequest,
    current_user: User = Depends(get_partner_user),
    db: AsyncSession = Depends(get_db),
):
    """Update hotel details. Only provided fields are updated."""
    updated = await hotel_service.update_hotel(hotel_id, data, current_user, db)
    return APIResponse.success(message="Hotel updated", data=updated)
 
 
@router.delete("/partner/{hotel_id}", response_model=APIResponse,
               summary="[Partner] Delete hotel")
async def delete_hotel(
    hotel_id: str,
    current_user: User = Depends(get_partner_user),
    db: AsyncSession = Depends(get_db),
):
    """Permanently delete a hotel and all its rooms, images, and amenities."""
    result = await hotel_service.delete_hotel(hotel_id, current_user, db)
    return APIResponse.success(message=result["message"])
 
 
@router.put("/partner/{hotel_id}/toggle-status", response_model=APIResponse,
            summary="[Partner] Toggle hotel active status")
async def toggle_hotel_status(
    hotel_id: str,
    current_user: User = Depends(get_partner_user),
    db: AsyncSession = Depends(get_db),
):
    """Activate or deactivate a hotel. Deactivated hotels do not show in public listings."""
    result = await hotel_service.toggle_hotel_status(hotel_id, current_user, db)
    return APIResponse.success(message=result["message"], data=result)
 
 
# ── ROOMS ──────────────────────────────────────────────────────────────
 
@router.post("/partner/{hotel_id}/rooms", response_model=APIResponse, status_code=201,
             summary="[Partner] Add room type")
async def add_room(
    hotel_id: str,
    data: RoomCreateRequest,
    current_user: User = Depends(get_partner_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Add a new room type to the hotel.
    room_type: STANDARD | DELUXE | SUITE | FAMILY | DORMITORY
    Also updates hotel base_price to the lowest active room price.
    """
    room = await hotel_service.add_room(hotel_id, data, current_user, db)
    return APIResponse.success(message="Room added successfully", data=room)
 
 
@router.put("/partner/{hotel_id}/rooms/{room_id}", response_model=APIResponse,
            summary="[Partner] Update room type")
async def update_room(
    hotel_id: str,
    room_id: str,
    data: RoomUpdateRequest,
    current_user: User = Depends(get_partner_user),
    db: AsyncSession = Depends(get_db),
):
    """Update room details. Only provided fields are updated."""
    room = await hotel_service.update_room(hotel_id, room_id, data, current_user, db)
    return APIResponse.success(message="Room updated", data=room)
 
 
@router.delete("/partner/{hotel_id}/rooms/{room_id}", response_model=APIResponse,
               summary="[Partner] Delete room type")
async def delete_room(
    hotel_id: str,
    room_id: str,
    current_user: User = Depends(get_partner_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a room type. Also recalculates hotel base_price."""
    result = await hotel_service.delete_room(hotel_id, room_id, current_user, db)
    return APIResponse.success(message=result["message"])
 
 
# ── IMAGES ──────────────────────────────────────────────────────────────
 
@router.post("/partner/{hotel_id}/images", response_model=APIResponse, status_code=201,
             summary="[Partner] Upload hotel image")
async def upload_image(
    hotel_id: str,
    file: UploadFile = File(...),
    category:   str  = Query("EXTERIOR", description="EXTERIOR | INTERIOR | ROOM | RESTAURANT | POOL | OTHER"),
    caption:    str  = Query(None, description="Image caption"),
    is_primary: bool = Query(False, description="Set as primary/cover image"),
    current_user: User = Depends(get_partner_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload an image for the hotel. Stored in AWS S3.
    Setting is_primary=true clears the previous primary flag.
    """
    image = await hotel_service.upload_image(
        hotel_id, file, category, caption, is_primary, current_user, db
    )
    return APIResponse.success(message="Image uploaded successfully", data=image)
 
 
@router.delete("/partner/{hotel_id}/images/{image_id}", response_model=APIResponse,
               summary="[Partner] Delete hotel image")
async def delete_image(
    hotel_id: str,
    image_id: str,
    current_user: User = Depends(get_partner_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a hotel image from S3 and the database."""
    result = await hotel_service.delete_image(hotel_id, image_id, current_user, db)
    return APIResponse.success(message=result["message"])
 
 
# ── AMENITIES ──────────────────────────────────────────────────────────
 
@router.get("/partner/{hotel_id}/amenities", response_model=APIResponse,
            summary="[Partner] List hotel amenities")
async def list_amenities(
    hotel_id: str,
    current_user: User = Depends(get_partner_user),
    db: AsyncSession = Depends(get_db),
):
    """List all amenities for a hotel."""
    data = await hotel_service.list_amenities(hotel_id, current_user, db)
    return APIResponse.success(message=f"{len(data)} amenities", data=data)
 
 
@router.post("/partner/{hotel_id}/amenities", response_model=APIResponse, status_code=201,
             summary="[Partner] Add hotel amenity")
async def add_amenity(
    hotel_id: str,
    data: AmenityCreateRequest,
    current_user: User = Depends(get_partner_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Add an amenity to the hotel.
    category: GENERAL | WELLNESS | DINING | TRANSPORT | RELIGIOUS | KIDS
    """
    amenity = await hotel_service.add_amenity(hotel_id, data, current_user, db)
    return APIResponse.success(message="Amenity added", data=amenity)
 
 
@router.delete("/partner/{hotel_id}/amenities/{amenity_id}", response_model=APIResponse,
               summary="[Partner] Delete hotel amenity")
async def delete_amenity(
    hotel_id: str,
    amenity_id: str,
    current_user: User = Depends(get_partner_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove an amenity from the hotel."""
    result = await hotel_service.delete_amenity(hotel_id, amenity_id, current_user, db)
    return APIResponse.success(message=result["message"])