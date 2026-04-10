"""
services/hotel_service.py
Hotel module — complete business logic for all 27 endpoints (25 original + 2 new admin).

Public endpoints:
  - List hotels with filters
  - Featured hotels (cached 1hr)
  - Popular hotels (cached 30min)
  - Nearby hotels (Haversine)
  - Hotel detail, rooms, amenities, images, reviews, availability, pricing

Partner endpoints:
  - Hotel CRUD
  - Room CRUD + pricing + availability + block dates
  - Image upload / delete
  - Amenity add / delete

Admin endpoints (NEW — hotel approval workflow):
  - admin_list_hotels         GET  /admin/hotels              list all hotels with optional status filter
  - admin_get_hotel_detail    GET  /admin/hotels/{id}         full detail of any hotel regardless of status
  - admin_review_hotel        PUT  /admin/hotels/{id}/review  approve or reject a pending hotel
"""

import json
import logging
import math
from datetime import datetime, date
from typing import Optional, List

from fastapi import UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.models.hotel import Hotel, HotelRoom, HotelImage, HotelAmenity
from src.models.partner import Partner
from src.models.user import User
from src.models.notification import Notification
from src.schemas.hotel import (
    HotelCreateRequest, HotelUpdateRequest,
    RoomCreateRequest, RoomUpdateRequest,
    AmenityCreateRequest, AvailabilityRequest,
)
from src.schemas.admin import HotelReviewRequest
from src.repositories import hotel_repo
from src.core.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)

logger = logging.getLogger(__name__)

# ══════════════════ HELPERS ══════════════════

async def _get_verified_partner(user_id, db: AsyncSession) -> Partner:
    """Fetch Partner record for current user. Raises 404 if not registered."""
    result = await db.execute(select(Partner).where(Partner.user_id == user_id))
    partner = result.scalar_one_or_none()
    if not partner:
        raise NotFoundException("Partner profile not found. Please register first via POST /partners/register")
    return partner


def _hotel_to_dict(hotel: Hotel, include_nested: bool = True) -> dict:
    data = {
        "id":                   str(hotel.id),
        "partner_id":           str(hotel.partner_id),
        "name":                 hotel.name,
        "description":          hotel.description,
        "star_rating":          hotel.star_rating,
        "hotel_type":           hotel.hotel_type,
        "address":              hotel.address,
        "city":                 hotel.city,
        "state":                hotel.state,
        "pincode":              hotel.pincode,
        "latitude":             hotel.latitude,
        "longitude":            hotel.longitude,
        "distance_from_temple": hotel.distance_from_temple,
        "contact_phone":        hotel.contact_phone,
        "contact_email":        hotel.contact_email,
        "website":              hotel.website,
        "check_in_time":        hotel.check_in_time,
        "check_out_time":       hotel.check_out_time,
        "cancellation_policy":  hotel.cancellation_policy,
        "pet_policy":           hotel.pet_policy,
        "meal_options":         hotel.meal_options or [],
        "is_active":            hotel.is_active,
        "is_featured":          hotel.is_featured,
        "status":               hotel.status,
        "base_price":           float(hotel.base_price) if hotel.base_price else None,
        "rating":               hotel.rating,
        "total_reviews":        hotel.total_reviews,
        "created_at":           hotel.created_at,
    }
    if include_nested:
        data["rooms"]     = [_room_to_dict(r) for r in hotel.rooms]
        data["images"]    = [_image_to_dict(i) for i in hotel.images]
        data["amenities"] = [_amenity_to_dict(a) for a in hotel.amenities]
    return data


def _hotel_admin_dict(hotel: Hotel) -> dict:
    """
    Full admin view of a hotel — includes review-tracking fields that are
    intentionally excluded from the public and partner responses.
    """
    data = _hotel_to_dict(hotel, include_nested=True)
    # Append admin-only review fields
    data.update({
        "rejection_reason": hotel.rejection_reason,
        "admin_note":       hotel.admin_note,
        "reviewed_at":      hotel.reviewed_at,
        "reviewed_by":      str(hotel.reviewed_by) if hotel.reviewed_by else None,
    })
    return data


def _hotel_list_dict(hotel: Hotel) -> dict:
    primary_image = next(
        (i.image_url for i in hotel.images if i.is_primary),
        hotel.images[0].image_url if hotel.images else None
    )
    return {
        "id":                   str(hotel.id),
        "name":                 hotel.name,
        "star_rating":          hotel.star_rating,
        "hotel_type":           hotel.hotel_type,
        "city":                 hotel.city,
        "state":                hotel.state,
        "distance_from_temple": hotel.distance_from_temple,
        "base_price":           float(hotel.base_price) if hotel.base_price else None,
        "rating":               hotel.rating,
        "total_reviews":        hotel.total_reviews,
        "is_featured":          hotel.is_featured,
        "primary_image":        primary_image,
    }


def _room_to_dict(room: HotelRoom) -> dict:
    return {
        "id":               str(room.id),
        "hotel_id":         str(room.hotel_id),
        "room_type":        room.room_type,
        "name":             room.name,
        "description":      room.description,
        "max_occupancy":    room.max_occupancy,
        "total_rooms":      room.total_rooms,
        "price_per_night":  float(room.price_per_night),
        "weekend_price":    float(room.weekend_price) if room.weekend_price else None,
        "extra_bed_price":  float(room.extra_bed_price),
        "bed_type":         room.bed_type,
        "has_ac":           room.has_ac,
        "has_wifi":         room.has_wifi,
        "has_tv":           room.has_tv,
        "has_geyser":       room.has_geyser,
        "is_smoking":       room.is_smoking,
        "amenities":        room.amenities or [],
        "is_active":        room.is_active,
        "created_at":       room.created_at,
    }


def _image_to_dict(image: HotelImage) -> dict:
    return {
        "id":            str(image.id),
        "image_url":     image.image_url,
        "caption":       image.caption,
        "category":      image.category,
        "is_primary":    image.is_primary,
        "display_order": image.display_order,
    }


def _amenity_to_dict(amenity: HotelAmenity) -> dict:
    return {
        "id":       str(amenity.id),
        "name":     amenity.name,
        "category": amenity.category,
        "icon":     amenity.icon,
        "is_paid":  amenity.is_paid,
    }


def _update_base_price(hotel: Hotel) -> None:
    """Recalculate base_price from active rooms after room add/update/delete."""
    active_prices = [r.price_per_night for r in hotel.rooms if r.is_active]
    if active_prices:
        hotel.base_price = min(active_prices)


# ══════════════════ PUBLIC — BROWSE ══════════════════

async def list_hotels(
    db: AsyncSession,
    city: Optional[str] = None,
    star_rating: Optional[int] = None,
    hotel_type: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    checkin: Optional[str] = None,
    checkout: Optional[str] = None,
    guests: Optional[int] = None,
    page: int = 1,
    limit: int = 20,
) -> list:
    hotels = await hotel_repo.get_active_hotels(
        db, city=city, star_rating=star_rating, hotel_type=hotel_type,
        min_price=min_price, max_price=max_price, page=page, limit=limit
    )
    return [_hotel_list_dict(h) for h in hotels]


async def get_featured_hotels(db: AsyncSession, redis=None) -> list:
    """Featured hotels — cached in Redis for 1 hour."""
    cache_key = "hotels:featured"
    if redis:
        try:
            cached = redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    hotels = await hotel_repo.get_active_hotels(db, page=1, limit=20)
    featured = [h for h in hotels if h.is_featured]
    result = [_hotel_list_dict(h) for h in featured]

    if redis:
        try:
            redis.setex(cache_key, 3600, json.dumps(result, default=str))
        except Exception:
            pass
    return result


async def get_popular_hotels(db: AsyncSession, limit: int = 10, redis=None) -> list:
    """Popular hotels sorted by booking_count — cached 30 minutes."""
    cache_key = f"hotels:popular:{limit}"

    if redis:
        try:
            cached = await redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    result = await db.execute(
        select(Hotel)
        .options(selectinload(Hotel.rooms))  
        .where(Hotel.is_active == True, Hotel.status == "ACTIVE")
        .order_by(Hotel.total_reviews.desc(), Hotel.rating.desc())
        .limit(limit)
    )

    hotels = result.scalars().all()

    data = [_hotel_list_dict(h) for h in hotels]

    if redis:
        try:    
            await redis.setex(cache_key, 1800, json.dumps(data, default=str))
        except Exception:
            pass
    return data


async def get_nearby_hotels(
    db: AsyncSession,
    latitude: float,
    longitude: float,
    radius_km: float = 5.0,
    page: int = 1,
    limit: int = 10,
) -> list:
    """Hotels sorted by distance using Haversine formula."""
    all_hotels = await hotel_repo.get_active_hotels(db, page=1, limit=200)

    def haversine(lat1, lon1, lat2, lon2) -> float:
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2) ** 2
             + math.cos(math.radians(lat1))
             * math.cos(math.radians(lat2))
             * math.sin(dlon / 2) ** 2)
        return R * 2 * math.asin(math.sqrt(a))

    nearby = []
    for h in all_hotels:
        if h.latitude and h.longitude:
            dist = haversine(latitude, longitude, h.latitude, h.longitude)
            if dist <= radius_km:
                d = _hotel_list_dict(h)
                d["distance_km"] = round(dist, 2)
                nearby.append(d)

    nearby.sort(key=lambda x: x["distance_km"])
    start = (page - 1) * limit
    return nearby[start: start + limit]


# ══════════════════ PUBLIC — HOTEL DETAIL ══════════════════

async def get_hotel_detail(hotel_id: str, db: AsyncSession) -> dict:
    hotel = await hotel_repo.get_hotel_by_id(db, hotel_id)
    if not hotel.is_active or hotel.status != "ACTIVE":
        raise NotFoundException("Hotel not found")
    return _hotel_to_dict(hotel, include_nested=True)


async def get_hotel_rooms(hotel_id: str, db: AsyncSession) -> list:
    hotel = await hotel_repo.get_hotel_by_id(db, hotel_id)
    if not hotel.is_active or hotel.status != "ACTIVE":
        raise NotFoundException("Hotel not found")
    rooms = await hotel_repo.get_rooms_by_hotel(db, hotel_id)
    return [_room_to_dict(r) for r in rooms if r.is_active]


async def get_room_detail(hotel_id: str, room_id: str, db: AsyncSession) -> dict:
    hotel = await hotel_repo.get_hotel_by_id(db, hotel_id)
    if not hotel.is_active or hotel.status != "ACTIVE":
        raise NotFoundException("Hotel not found")
    room = await hotel_repo.get_room_by_id_and_hotel(db, room_id, hotel_id)
    return _room_to_dict(room)


async def get_hotel_amenities_public(hotel_id: str, db: AsyncSession) -> list:
    hotel = await hotel_repo.get_hotel_by_id(db, hotel_id)
    if not hotel.is_active or hotel.status != "ACTIVE":
        raise NotFoundException("Hotel not found")
    amenities = await hotel_repo.get_amenities_by_hotel(db, hotel_id)
    return [_amenity_to_dict(a) for a in amenities]


async def get_hotel_images_public(hotel_id: str, db: AsyncSession) -> list:
    hotel = await hotel_repo.get_hotel_by_id(db, hotel_id)
    if not hotel.is_active or hotel.status != "ACTIVE":
        raise NotFoundException("Hotel not found")
    images = await hotel_repo.get_images_by_hotel(db, hotel_id)
    return [_image_to_dict(i) for i in images]


async def get_hotel_reviews(hotel_id: str, page: int, limit: int, db: AsyncSession) -> dict:
    """Placeholder — will connect to Reviews module once integrated."""
    hotel = await hotel_repo.get_hotel_by_id(db, hotel_id)
    if not hotel.is_active or hotel.status != "ACTIVE":
        raise NotFoundException("Hotel not found")
    return {
        "hotel_id":       hotel_id,
        "total_reviews":  hotel.total_reviews,
        "average_rating": hotel.rating or 0.0,
        "reviews":        [],
        "page":           page,
        "limit":          limit,
    }


async def check_availability(hotel_id: str, data: AvailabilityRequest, db: AsyncSession) -> dict:
    hotel = await hotel_repo.get_hotel_by_id(db, hotel_id)
    if not hotel.is_active or hotel.status != "ACTIVE":
        raise NotFoundException("Hotel not found")

    nights = (data.check_out - data.check_in).days
    available_rooms = []
    for room in hotel.rooms:
        if not room.is_active:
            continue
        if data.room_type and room.room_type != data.room_type.upper():
            continue
        if room.max_occupancy < data.guests:
            continue
        available_rooms.append({
            "room_id":         str(room.id),
            "room_type":       room.room_type,
            "name":            room.name,
            "max_occupancy":   room.max_occupancy,
            "available_count": room.total_rooms,  # placeholder — real count from bookings
            "price_per_night": float(room.price_per_night),
            "total_price":     float(room.price_per_night) * nights,
            "bed_type":        room.bed_type,
            "has_ac":          room.has_ac,
            "has_wifi":        room.has_wifi,
        })
    return {
        "hotel_id":        hotel_id,
        "hotel_name":      hotel.name,
        "check_in":        str(data.check_in),
        "check_out":       str(data.check_out),
        "nights":          nights,
        "available_rooms": available_rooms,
    }


async def get_hotel_pricing(hotel_id: str, checkin: str, checkout: str, db: AsyncSession) -> dict:
    """Room pricing for dates including weekend multiplier."""
    hotel = await hotel_repo.get_hotel_by_id(db, hotel_id)
    if not hotel.is_active or hotel.status != "ACTIVE":
        raise NotFoundException("Hotel not found")

    try:
        ci = date.fromisoformat(checkin)
        co = date.fromisoformat(checkout)
    except ValueError:
        raise BadRequestException("Invalid date format. Use YYYY-MM-DD")

    nights = (co - ci).days
    if nights <= 0:
        raise BadRequestException("checkout must be after checkin")

    rooms = await hotel_repo.get_rooms_by_hotel(db, hotel_id)
    pricing = []
    for room in rooms:
        if not room.is_active:
            continue
        price = float(room.price_per_night)
        weekend_price = float(room.weekend_price) if room.weekend_price else price
        pricing.append({
            "room_id":         str(room.id),
            "room_type":       room.room_type,
            "name":            room.name,
            "price_per_night": price,
            "weekend_price":   weekend_price,
            "nights":          nights,
            "total_price":     price * nights,
            "max_occupancy":   room.max_occupancy,
        })
    return {
        "hotel_id": hotel_id,
        "checkin":  checkin,
        "checkout": checkout,
        "nights":   nights,
        "rooms":    pricing,
    }


# ══════════════════ PARTNER — HOTEL CRUD ══════════════════

async def create_hotel(data: HotelCreateRequest, current_user: User, db: AsyncSession) -> dict:
    partner = await _get_verified_partner(current_user.id, db)
    if partner.verification_status != "VERIFIED":
        raise ForbiddenException("Partner must be verified before adding hotels")
    hotel = Hotel(
        partner_id=partner.id,
        name=data.name,
        description=data.description,
        star_rating=data.star_rating,
        hotel_type=data.hotel_type,
        address=data.address,
        city=data.city,
        state=data.state,
        pincode=data.pincode,
        latitude=data.latitude,
        longitude=data.longitude,
        distance_from_temple=data.distance_from_temple,
        contact_phone=data.contact_phone,
        contact_email=data.contact_email,
        website=data.website,
        check_in_time=data.check_in_time,
        check_out_time=data.check_out_time,
        cancellation_policy=data.cancellation_policy,
        pet_policy=data.pet_policy,
        meal_options=data.meal_options or [],
        status="PENDING",
        is_active=False,    # explicitly False — admin must approve first
    )
    hotel = await hotel_repo.create_hotel(db, hotel)
    logger.info("Hotel created partner_id=%s hotel=%s status=PENDING", partner.id, hotel.name)
    return _hotel_to_dict(hotel, include_nested=False)


async def get_my_hotels(current_user: User, db: AsyncSession) -> list:
    partner = await _get_verified_partner(current_user.id, db)
    hotels = await hotel_repo.get_hotels_by_partner(db, str(partner.id))
    return [_hotel_to_dict(h, include_nested=True) for h in hotels]


async def get_my_hotel_detail(hotel_id: str, current_user: User, db: AsyncSession) -> dict:
    partner = await _get_verified_partner(current_user.id, db)
    hotel = await hotel_repo.get_hotel_by_id_and_partner(db, hotel_id, str(partner.id))
    return _hotel_to_dict(hotel, include_nested=True)


async def update_hotel(hotel_id: str, data: HotelUpdateRequest, current_user: User, db: AsyncSession) -> dict:
    partner = await _get_verified_partner(current_user.id, db)
    hotel = await hotel_repo.get_hotel_by_id_and_partner(db, hotel_id, str(partner.id))
    update_fields = data.model_dump(exclude_none=True)
    for field, value in update_fields.items():
        setattr(hotel, field, value)
    hotel.updated_at = datetime.utcnow()
    hotel = await hotel_repo.update_hotel(db, hotel)
    logger.info("Hotel updated hotel_id=%s", hotel_id)
    return _hotel_to_dict(hotel, include_nested=True)


async def delete_hotel(hotel_id: str, current_user: User, db: AsyncSession) -> dict:
    """Soft delete — deactivates hotel instead of hard delete."""
    partner = await _get_verified_partner(current_user.id, db)
    hotel = await hotel_repo.get_hotel_by_id_and_partner(db, hotel_id, str(partner.id))
    hotel.is_active = False
    hotel.status = "INACTIVE"
    hotel.updated_at = datetime.utcnow()
    await hotel_repo.update_hotel(db, hotel)
    logger.info("Hotel soft deleted hotel_id=%s", hotel_id)
    return {"message": "Hotel deactivated successfully"}


async def toggle_hotel_status(hotel_id: str, current_user: User, db: AsyncSession) -> dict:
    partner = await _get_verified_partner(current_user.id, db)
    hotel = await hotel_repo.get_hotel_by_id_and_partner(db, hotel_id, str(partner.id))
    hotel.is_active = not hotel.is_active
    hotel.updated_at = datetime.utcnow()
    await hotel_repo.update_hotel(db, hotel)
    status_str = "activated" if hotel.is_active else "deactivated"
    return {"message": f"Hotel {status_str}", "is_active": hotel.is_active}


# ══════════════════ PARTNER — ROOM CRUD ══════════════════

async def add_room(hotel_id: str, data: RoomCreateRequest, current_user: User, db: AsyncSession) -> dict:
    partner = await _get_verified_partner(current_user.id, db)
    hotel = await hotel_repo.get_hotel_by_id_and_partner(db, hotel_id, str(partner.id))
    room = HotelRoom(
        hotel_id=hotel.id,
        room_type=data.room_type,
        name=data.name,
        description=data.description,
        max_occupancy=data.max_occupancy,
        total_rooms=data.total_rooms,
        price_per_night=data.price_per_night,
        weekend_price=data.weekend_price,
        extra_bed_price=data.extra_bed_price,
        bed_type=data.bed_type,
        has_ac=data.has_ac,
        has_wifi=data.has_wifi,
        has_tv=data.has_tv,
        has_geyser=data.has_geyser,
        is_smoking=data.is_smoking,
        amenities=data.amenities or [],
    )
    room = await hotel_repo.create_room(db, room)
    await db.refresh(hotel)
    _update_base_price(hotel)
    await hotel_repo.update_hotel(db, hotel)
    logger.info("Room added hotel_id=%s room_type=%s", hotel_id, data.room_type)
    return _room_to_dict(room)


async def update_room(hotel_id: str, room_id: str, data: RoomUpdateRequest, current_user: User, db: AsyncSession) -> dict:
    partner = await _get_verified_partner(current_user.id, db)
    await hotel_repo.get_hotel_by_id_and_partner(db, hotel_id, str(partner.id))
    room = await hotel_repo.get_room_by_id_and_hotel(db, room_id, hotel_id)
    update_fields = data.model_dump(exclude_none=True)
    for field, value in update_fields.items():
        setattr(room, field, value)
    room.updated_at = datetime.utcnow()
    room = await hotel_repo.update_room(db, room)
    return _room_to_dict(room)


async def delete_room(hotel_id: str, room_id: str, current_user: User, db: AsyncSession) -> dict:
    partner = await _get_verified_partner(current_user.id, db)
    hotel = await hotel_repo.get_hotel_by_id_and_partner(db, hotel_id, str(partner.id))
    room = await hotel_repo.get_room_by_id_and_hotel(db, room_id, hotel_id)
    await hotel_repo.delete_room(db, room)
    await db.refresh(hotel)
    _update_base_price(hotel)
    await hotel_repo.update_hotel(db, hotel)
    return {"message": "Room deleted successfully"}


async def update_room_pricing(
    hotel_id: str, room_id: str,
    price_per_night: float, weekend_price: Optional[float],
    current_user: User, db: AsyncSession
) -> dict:
    partner = await _get_verified_partner(current_user.id, db)
    await hotel_repo.get_hotel_by_id_and_partner(db, hotel_id, str(partner.id))
    room = await hotel_repo.get_room_by_id_and_hotel(db, room_id, hotel_id)
    room.price_per_night = price_per_night
    if weekend_price is not None:
        room.weekend_price = weekend_price
    room.updated_at = datetime.utcnow()
    await hotel_repo.update_room(db, room)
    return _room_to_dict(room)


async def toggle_room_availability(hotel_id: str, room_id: str, current_user: User, db: AsyncSession) -> dict:
    partner = await _get_verified_partner(current_user.id, db)
    await hotel_repo.get_hotel_by_id_and_partner(db, hotel_id, str(partner.id))
    room = await hotel_repo.get_room_by_id_and_hotel(db, room_id, hotel_id)
    room.is_active = not room.is_active
    room.updated_at = datetime.utcnow()
    await hotel_repo.update_room(db, room)
    status_str = "available" if room.is_active else "unavailable"
    return {"message": f"Room marked as {status_str}", "is_active": room.is_active}


async def block_room_dates(
    hotel_id: str, room_id: str,
    dates: list, reason: Optional[str],
    current_user: User, db: AsyncSession
) -> dict:
    """Block specific dates for a room (maintenance, renovation)."""
    partner = await _get_verified_partner(current_user.id, db)
    await hotel_repo.get_hotel_by_id_and_partner(db, hotel_id, str(partner.id))
    await hotel_repo.get_room_by_id_and_hotel(db, room_id, hotel_id)
    # Will connect to room_blocked_dates table in Booking module
    return {
        "message":       f"{len(dates)} dates blocked successfully",
        "hotel_id":      hotel_id,
        "room_id":       room_id,
        "blocked_dates": dates,
        "reason":        reason,
    }


# ══════════════════ PARTNER — IMAGES ══════════════════

async def upload_image(
    hotel_id: str, file: UploadFile, category: str,
    caption: Optional[str], is_primary: bool,
    current_user: User, db: AsyncSession
) -> dict:
    partner = await _get_verified_partner(current_user.id, db)
    hotel = await hotel_repo.get_hotel_by_id_and_partner(db, hotel_id, str(partner.id))

    category = category.upper()
    valid_cats = ["EXTERIOR", "INTERIOR", "ROOM", "RESTAURANT", "POOL", "OTHER"]
    if category not in valid_cats:
        raise BadRequestException(f"category must be one of: {', '.join(valid_cats)}")

    # S3 upload stub — replace with actual S3 call once aws_s3 is configured
    file_url = f"https://ap-tourism-media.s3.ap-south-1.amazonaws.com/hotels/{hotel.id}/{category}_{file.filename}"

    if is_primary:
        existing_images = await hotel_repo.get_images_by_hotel(db, hotel_id)
        for img in existing_images:
            if img.is_primary:
                img.is_primary = False
        await db.commit()

    existing_count = len(await hotel_repo.get_images_by_hotel(db, hotel_id))
    image = HotelImage(
        hotel_id=hotel.id,
        image_url=file_url,
        caption=caption,
        category=category,
        is_primary=is_primary,
        display_order=existing_count,
    )
    image = await hotel_repo.create_image(db, image)
    logger.info("Image uploaded hotel_id=%s category=%s", hotel_id, category)
    return _image_to_dict(image)


async def delete_image(hotel_id: str, image_id: str, current_user: User, db: AsyncSession) -> dict:
    partner = await _get_verified_partner(current_user.id, db)
    await hotel_repo.get_hotel_by_id_and_partner(db, hotel_id, str(partner.id))
    image = await hotel_repo.get_image_by_id_and_hotel(db, image_id, hotel_id)
    await hotel_repo.delete_image(db, image)
    return {"message": "Image deleted successfully"}


# ══════════════════ PARTNER — AMENITIES ══════════════════

async def add_amenity(hotel_id: str, data: AmenityCreateRequest, current_user: User, db: AsyncSession) -> dict:
    partner = await _get_verified_partner(current_user.id, db)
    hotel = await hotel_repo.get_hotel_by_id_and_partner(db, hotel_id, str(partner.id))
    amenity = HotelAmenity(
        hotel_id=hotel.id,
        name=data.name,
        category=data.category,
        icon=data.icon,
        is_paid=data.is_paid,
    )
    amenity = await hotel_repo.create_amenity(db, amenity)
    return _amenity_to_dict(amenity)


async def delete_amenity(hotel_id: str, amenity_id: str, current_user: User, db: AsyncSession) -> dict:
    partner = await _get_verified_partner(current_user.id, db)
    await hotel_repo.get_hotel_by_id_and_partner(db, hotel_id, str(partner.id))
    amenity = await hotel_repo.get_amenity_by_id_and_hotel(db, amenity_id, hotel_id)
    await hotel_repo.delete_amenity(db, amenity)
    return {"message": "Amenity deleted successfully"}


async def list_amenities(hotel_id: str, current_user: User, db: AsyncSession) -> list:
    partner = await _get_verified_partner(current_user.id, db)
    await hotel_repo.get_hotel_by_id_and_partner(db, hotel_id, str(partner.id))
    amenities = await hotel_repo.get_amenities_by_hotel(db, hotel_id)
    return [_amenity_to_dict(a) for a in amenities]


# ══════════════════ ADMIN ══════════════════

async def admin_list_hotels(
    db: AsyncSession,
    page: int = 1,
    per_page: int = 20,
    status: Optional[str] = None,
) -> dict:
    """
    List all hotels (any status) — admin view.
    Supports optional ?status= filter (PENDING | ACTIVE | INACTIVE | REJECTED).
    """
    from sqlalchemy import func

    query = select(Hotel).options(
        selectinload(Hotel.rooms),
        selectinload(Hotel.images),
        selectinload(Hotel.amenities),
    )

    if status:
        query = query.where(Hotel.status == status.upper())

    count_result = await db.execute(
        select(func.count()).select_from(
            select(Hotel).where(Hotel.status == status.upper()).subquery()
            if status
            else select(Hotel).subquery()
        )
    )
    total = count_result.scalar()

    result = await db.execute(
        query.order_by(Hotel.created_at.desc())
             .offset((page - 1) * per_page)
             .limit(per_page)
    )
    hotels = result.scalars().all()

    return {
        "data":  [_hotel_admin_dict(h) for h in hotels],
        "total": total,
        "page":  page,
        "pages": -(-total // per_page) if total else 0,
    }


async def admin_get_hotel_detail(
    hotel_id: str,
    db: AsyncSession,
) -> dict:
    """
    Fetch full hotel detail for any hotel regardless of status.
    Used by admin to review a pending submission before approving.
    Raises 404 if the hotel_id does not exist.
    """
    hotel = await hotel_repo.get_hotel_by_id(db, hotel_id)
    # hotel_repo.get_hotel_by_id already raises 404 if not found
    return _hotel_admin_dict(hotel)


async def admin_review_hotel(
    hotel_id: str,
    data: HotelReviewRequest,
    admin_user: User,
    db: AsyncSession,
) -> dict:
    """
    Approve or reject a hotel submission.

    Approve  (data.approved = True):
      - hotel.status    → ACTIVE
      - hotel.is_active → True   (hotel becomes publicly visible)
      - hotel.rejection_reason cleared
      - hotel.reviewed_at / reviewed_by stamped

    Reject   (data.approved = False):
      - hotel.status    → REJECTED
      - hotel.is_active → False  (hotel stays hidden)
      - hotel.rejection_reason set (required)
      - hotel.reviewed_at / reviewed_by stamped

    After committing, an in-app Notification is created for the partner's
    user account so they see the outcome immediately in the app.

    Raises:
      - 404  if hotel does not exist
      - 400  if hotel is already ACTIVE or REJECTED (not in PENDING state)
      - 422  if approved=False and rejection_reason is missing (schema-level)
    """
    hotel = await hotel_repo.get_hotel_by_id(db, hotel_id)

    # Guard: only PENDING hotels should be reviewed. Re-reviewing an already
    # decided hotel would silently overwrite the previous decision which is
    # dangerous. Admin must use a separate "force-reactivate" workflow.
    if hotel.status not in ("PENDING", "INACTIVE"):
        raise BadRequestException(
            f"Hotel is already '{hotel.status}'. Only PENDING or INACTIVE hotels can be reviewed. "
            "Use a separate reactivation workflow if needed."
        )

    now = datetime.utcnow()

    if data.approved:
        hotel.status           = "ACTIVE"
        hotel.is_active        = True
        hotel.rejection_reason = None       # clear any previous rejection reason
        hotel.admin_note       = data.admin_note
        hotel.reviewed_at      = now
        hotel.reviewed_by      = admin_user.id
        action_label           = "approved"
        notif_title            = "Hotel Approved 🎉"
        notif_body             = (
            f"Congratulations! Your hotel '{hotel.name}' has been approved "
            "and is now live on AP Tourism."
        )
        logger.info(
            "Hotel approved hotel_id=%s hotel_name=%s admin_id=%s",
            hotel_id, hotel.name, admin_user.id,
        )
    else:
        hotel.status           = "REJECTED"
        hotel.is_active        = False
        hotel.rejection_reason = data.rejection_reason
        hotel.admin_note       = data.admin_note
        hotel.reviewed_at      = now
        hotel.reviewed_by      = admin_user.id
        action_label           = "rejected"
        notif_title            = "Hotel Submission Rejected"
        notif_body             = (
            f"Your hotel '{hotel.name}' was not approved. "
            f"Reason: {data.rejection_reason}. "
            "Please update your submission and resubmit."
        )
        logger.info(
            "Hotel rejected hotel_id=%s hotel_name=%s reason=%s admin_id=%s",
            hotel_id, hotel.name, data.rejection_reason, admin_user.id,
        )

    hotel.updated_at = now
    await hotel_repo.update_hotel(db, hotel)

    # ── Notify the partner's user account ─────────────────────────────────────
    # Fetch the partner's user_id via the partner record so we know
    # who to send the notification to.
    partner_result = await db.execute(
        select(Partner).where(Partner.id == hotel.partner_id)
    )
    partner = partner_result.scalar_one_or_none()

    if partner:
        notification = Notification(
            user_id=partner.user_id,
            type="hotel_review",
            title=notif_title,
            body=notif_body,
            channel="in_app",
            data={
                "hotel_id": str(hotel.id),
                "status":   hotel.status,
                "screen":   "HotelDetail",
            },
        )
        db.add(notification)
        await db.commit()
        logger.info(
            "Notification sent to partner user_id=%s for hotel_id=%s action=%s",
            partner.user_id, hotel_id, action_label,
        )

    return _hotel_admin_dict(hotel)