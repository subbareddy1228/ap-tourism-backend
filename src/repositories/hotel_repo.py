import uuid
from typing import List, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, select, func
from fastapi import HTTPException

from src.models.hotel import Hotel, HotelRoom, HotelRoomBlock
from src.schemas.hotel import (
    HotelCreateSchema, HotelUpdateSchema,
    RoomCreateSchema, RoomUpdateSchema
)


class HotelPartnerRepository:

    # ─── Hotel Queries ────────────────────────────────────────

    async def get_hotel_by_id(self, db: AsyncSession, hotel_id: str) -> Optional[Hotel]:
        result = await db.execute(select(Hotel).where(Hotel.id == hotel_id))
        return result.scalar_one_or_none()

    async def get_partner_hotel(
        self, db: AsyncSession, hotel_id: str, partner_id: str
    ) -> Optional[Hotel]:
        result = await db.execute(
            select(Hotel).where(
                and_(Hotel.id == hotel_id, Hotel.partner_id == partner_id)
            )
        )
        return result.scalar_one_or_none()

    async def get_partner_hotels(
        self, db: AsyncSession, partner_id: str, page: int, limit: int
    ) -> Tuple[List[Hotel], int]:
        count_result = await db.execute(
            select(func.count()).select_from(Hotel).where(Hotel.partner_id == partner_id)
        )
        total = count_result.scalar()

        result = await db.execute(
            select(Hotel)
            .where(Hotel.partner_id == partner_id)
            .offset((page - 1) * limit)
            .limit(limit)
        )
        hotels = result.scalars().all()
        return hotels, total

    # ─── Hotel CRUD ───────────────────────────────────────────

    async def create_hotel(
        self, db: AsyncSession, data: HotelCreateSchema, partner_id: str
    ) -> Hotel:
        hotel = Hotel(
            partner_id          = partner_id,
            name                = data.name,
            description         = data.description,
            address_line1       = data.address_line1,
            address_line2       = data.address_line2,
            city                = data.city,
            district            = data.district,
            state               = data.state,
            pincode             = data.pincode,
            latitude            = data.latitude,
            longitude           = data.longitude,
            star_rating         = data.star_rating,
            check_in_time       = data.check_in_time,
            check_out_time      = data.check_out_time,
            cancellation_policy = data.cancellation_policy,
            amenities           = data.amenities,
            phone               = data.phone,
            email               = data.email,
            website             = data.website,
            images              = [],
            is_active           = True
        )
        db.add(hotel)
        await db.commit()
        await db.refresh(hotel)
        return hotel

    async def update_hotel(
        self, db: AsyncSession, hotel: Hotel, data: HotelUpdateSchema
    ) -> Hotel:
        update_data = data.model_dump(exclude_none=True)
        for field, value in update_data.items():
            setattr(hotel, field, value)
        await db.commit()
        await db.refresh(hotel)
        return hotel

    async def soft_delete_hotel(self, db: AsyncSession, hotel: Hotel) -> Hotel:
        hotel.is_active = False
        await db.commit()
        await db.refresh(hotel)
        return hotel

    # ─── Room Queries ─────────────────────────────────────────

    async def get_room_by_id(
        self, db: AsyncSession, hotel_id: str, room_id: str
    ) -> Optional[HotelRoom]:
        result = await db.execute(
            select(HotelRoom).where(
                and_(HotelRoom.id == room_id, HotelRoom.hotel_id == hotel_id)
            )
        )
        return result.scalar_one_or_none()

    async def get_hotel_rooms(
        self, db: AsyncSession, hotel_id: str
    ) -> List[HotelRoom]:
        result = await db.execute(
            select(HotelRoom).where(HotelRoom.hotel_id == hotel_id)
        )
        return result.scalars().all()

    # ─── Room CRUD ────────────────────────────────────────────

    async def create_room(
        self, db: AsyncSession, hotel_id: str, data: RoomCreateSchema
    ) -> HotelRoom:
        room = HotelRoom(
            hotel_id        = hotel_id,
            name            = data.name,
            description     = data.description,
            room_type       = data.room_type,
            capacity        = data.capacity,
            price_per_night = data.price_per_night,
            total_rooms     = data.total_rooms,
            available_rooms = data.total_rooms,
            amenities       = data.amenities,
            images          = [],
            is_active       = True
        )
        db.add(room)
        await db.commit()
        await db.refresh(room)
        return room

    async def update_room(
        self, db: AsyncSession, room: HotelRoom, data: RoomUpdateSchema
    ) -> HotelRoom:
        update_data = data.model_dump(exclude_none=True)
        for field, value in update_data.items():
            setattr(room, field, value)
        await db.commit()
        await db.refresh(room)
        return room

    async def delete_room(self, db: AsyncSession, room: HotelRoom):
        await db.delete(room)
        await db.commit()

    async def update_room_pricing(
        self, db: AsyncSession, room: HotelRoom, price: float
    ) -> HotelRoom:
        room.price_per_night = price
        await db.commit()
        await db.refresh(room)
        return room

    async def toggle_room_availability(
        self, db: AsyncSession, room: HotelRoom, is_active: bool
    ) -> HotelRoom:
        room.is_active = is_active
        await db.commit()
        await db.refresh(room)
        return room

    async def block_room_dates(
        self, db: AsyncSession, room_id: str, dates: List[str], reason: Optional[str]
    ) -> List[HotelRoomBlock]:
        blocks = []
        for date in dates:
            result = await db.execute(
                select(HotelRoomBlock).where(
                    and_(
                        HotelRoomBlock.room_id == room_id,
                        HotelRoomBlock.block_date == date
                    )
                )
            )
            existing = result.scalar_one_or_none()
            if not existing:
                block = HotelRoomBlock(
                    room_id    = room_id,
                    block_date = date,
                    reason     = reason
                )
                db.add(block)
                blocks.append(block)
        await db.commit()
        return blocks

    # ─── Images ───────────────────────────────────────────────

    async def add_image(
        self, db: AsyncSession, hotel: Hotel, image_url: str
    ) -> Hotel:
        images = list(hotel.images or [])
        if len(images) >= 20:
            raise HTTPException(
                status_code=400,
                detail="Maximum 20 images allowed per hotel"
            )
        images.append({"id": str(uuid.uuid4()), "url": image_url})
        hotel.images = images
        await db.commit()
        await db.refresh(hotel)
        return hotel

    async def delete_image(
        self, db: AsyncSession, hotel: Hotel, image_id: str
    ) -> Hotel:
        images = [img for img in (hotel.images or []) if img.get("id") != image_id]
        if len(images) == len(hotel.images or []):
            raise HTTPException(status_code=404, detail="Image not found")
        hotel.images = images
        await db.commit()
        await db.refresh(hotel)
        return hotel

    # ─── Amenities ────────────────────────────────────────────

    async def add_amenity(
        self, db: AsyncSession, hotel: Hotel, amenity: str
    ) -> Hotel:
        amenities = list(hotel.amenities or [])
        if amenity in amenities:
            raise HTTPException(status_code=409, detail="Amenity already exists")
        amenities.append(amenity)
        hotel.amenities = amenities
        await db.commit()
        await db.refresh(hotel)
        return hotel

    async def delete_amenity(
        self, db: AsyncSession, hotel: Hotel, amenity_id: int
    ) -> Hotel:
        amenities = list(hotel.amenities or [])
        if amenity_id < 0 or amenity_id >= len(amenities):
            raise HTTPException(status_code=404, detail="Amenity not found")
        amenities.pop(amenity_id)
        hotel.amenities = amenities
        await db.commit()
        await db.refresh(hotel)
        return hotel


hotel_partner_repo = HotelPartnerRepository()
