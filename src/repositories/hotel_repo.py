"""
repositories/hotel_repo.py
Database access layer for the Hotel module.
All queries use SQLAlchemy async — same pattern as partner_repo / user_repo.
"""

from typing import Optional, List
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from src.models.hotel import Hotel, HotelRoom, HotelImage, HotelAmenity


# ══════════════════ HOTEL ══════════════════

async def get_hotel_by_id(db: AsyncSession, hotel_id: str) -> Hotel:
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Hotel).options(
            selectinload(Hotel.rooms),
            selectinload(Hotel.images),
            selectinload(Hotel.amenities),
        ).where(Hotel.id == hotel_id)
    )
    hotel = result.scalar_one_or_none()
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")
    return hotel


async def get_hotel_by_id_and_partner(db: AsyncSession, hotel_id: str, partner_id: str) -> Hotel:
    result = await db.execute(
        select(Hotel).where(
            and_(Hotel.id == hotel_id, Hotel.partner_id == partner_id)
        )
    )
    hotel = result.scalar_one_or_none()
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found or access denied")
    return hotel


async def get_hotels_by_partner(db: AsyncSession, partner_id: str) -> List[Hotel]:
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Hotel).options(
            selectinload(Hotel.rooms),
            selectinload(Hotel.images),
            selectinload(Hotel.amenities),
        )
        .where(Hotel.partner_id == partner_id)
        .order_by(Hotel.created_at.desc())
    )
    return result.scalars().all()


async def get_active_hotels(
    db: AsyncSession,
    city: Optional[str] = None,
    star_rating: Optional[int] = None,
    hotel_type: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    page: int = 1,
    limit: int = 20,
) -> List[Hotel]:
    from sqlalchemy.orm import selectinload
    query = select(Hotel).options(
        selectinload(Hotel.rooms),
        selectinload(Hotel.images),
        selectinload(Hotel.amenities),
    ).where(
        Hotel.is_active == True,
        Hotel.status == "ACTIVE"
    )
    if city:
        query = query.where(Hotel.city.ilike(f"%{city}%"))
    if star_rating:
        query = query.where(Hotel.star_rating == star_rating)
    if hotel_type:
        query = query.where(Hotel.hotel_type == hotel_type.upper())
    if min_price is not None:
        query = query.where(Hotel.base_price >= min_price)
    if max_price is not None:
        query = query.where(Hotel.base_price <= max_price)

    query = query.order_by(Hotel.is_featured.desc(), Hotel.rating.desc())
    query = query.offset((page - 1) * limit).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()

async def create_hotel(db: AsyncSession, hotel: Hotel) -> Hotel:
    db.add(hotel)
    await db.commit()
    await db.refresh(hotel)
    return hotel


async def update_hotel(db: AsyncSession, hotel: Hotel) -> Hotel:
    await db.commit()
    await db.refresh(hotel)
    return hotel


async def delete_hotel(db: AsyncSession, hotel: Hotel) -> None:
    await db.delete(hotel)
    await db.commit()


# ══════════════════ HOTEL ROOM ══════════════════

async def get_room_by_id(db: AsyncSession, room_id: str) -> HotelRoom:
    result = await db.execute(
        select(HotelRoom).where(HotelRoom.id == room_id)
    )
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room


async def get_room_by_id_and_hotel(db: AsyncSession, room_id: str, hotel_id: str) -> HotelRoom:
    result = await db.execute(
        select(HotelRoom).where(
            and_(HotelRoom.id == room_id, HotelRoom.hotel_id == hotel_id)
        )
    )
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room


async def get_rooms_by_hotel(db: AsyncSession, hotel_id: str) -> List[HotelRoom]:
    result = await db.execute(
        select(HotelRoom)
        .where(HotelRoom.hotel_id == hotel_id)
        .order_by(HotelRoom.price_per_night)
    )
    return result.scalars().all()


async def create_room(db: AsyncSession, room: HotelRoom) -> HotelRoom:
    db.add(room)
    await db.commit()
    await db.refresh(room)
    return room


async def update_room(db: AsyncSession, room: HotelRoom) -> HotelRoom:
    await db.commit()
    await db.refresh(room)
    return room


async def delete_room(db: AsyncSession, room: HotelRoom) -> None:
    await db.delete(room)
    await db.commit()


# ══════════════════ HOTEL IMAGE ══════════════════

async def get_image_by_id_and_hotel(db: AsyncSession, image_id: str, hotel_id: str) -> HotelImage:
    result = await db.execute(
        select(HotelImage).where(
            and_(HotelImage.id == image_id, HotelImage.hotel_id == hotel_id)
        )
    )
    image = result.scalar_one_or_none()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    return image


async def get_images_by_hotel(db: AsyncSession, hotel_id: str) -> List[HotelImage]:
    result = await db.execute(
        select(HotelImage)
        .where(HotelImage.hotel_id == hotel_id)
        .order_by(HotelImage.display_order)
    )
    return result.scalars().all()


async def create_image(db: AsyncSession, image: HotelImage) -> HotelImage:
    db.add(image)
    await db.commit()
    await db.refresh(image)
    return image


async def delete_image(db: AsyncSession, image: HotelImage) -> None:
    await db.delete(image)
    await db.commit()


# ══════════════════ HOTEL AMENITY ══════════════════

async def get_amenities_by_hotel(db: AsyncSession, hotel_id: str) -> List[HotelAmenity]:
    result = await db.execute(
        select(HotelAmenity).where(HotelAmenity.hotel_id == hotel_id)
    )
    return result.scalars().all()


async def get_amenity_by_id_and_hotel(db: AsyncSession, amenity_id: str, hotel_id: str) -> HotelAmenity:
    result = await db.execute(
        select(HotelAmenity).where(
            and_(HotelAmenity.id == amenity_id, HotelAmenity.hotel_id == hotel_id)
        )
    )
    amenity = result.scalar_one_or_none()
    if not amenity:
        raise HTTPException(status_code=404, detail="Amenity not found")
    return amenity


async def create_amenity(db: AsyncSession, amenity: HotelAmenity) -> HotelAmenity:
    db.add(amenity)
    await db.commit()
    await db.refresh(amenity)
    return amenity


async def delete_amenity(db: AsyncSession, amenity: HotelAmenity) -> None:
    await db.delete(amenity)
    await db.commit()
