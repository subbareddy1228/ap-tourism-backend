import os
import uuid
import aiofiles
from typing import List
from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.hotel_repo import hotel_partner_repo
from src.schemas.hotel import (
    HotelCreateSchema, HotelUpdateSchema,
    RoomCreateSchema, RoomUpdateSchema,
    RoomPricingSchema, RoomAvailabilitySchema,
    RoomBlockSchema, AmenityAddSchema
)
from src.common.responses import (
    success_response, created_response, list_response
)
from src.core.config import settings

import math
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/jpg", "image/webp"]
MAX_IMAGE_SIZE_MB   = 5


class HotelPartnerService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = hotel_partner_repo

    # ─── Helper — verify hotel ownership ─────────────────────

    async def get_owned_hotel(self, hotel_id: int, partner_id: str):
        hotel = await self.repo.get_partner_hotel(self.db, hotel_id, partner_id)
        if not hotel:
            raise HTTPException(
                status_code=404,
                detail="Hotel not found or you do not have permission to access it"
            )
        return hotel

    # ─── Hotel CRUD ───────────────────────────────────────────

    async def create_hotel(self, data: HotelCreateSchema, partner_id: str):
        hotel = await self.repo.create_hotel(self.db, data, partner_id)
        return created_response(
            data    = hotel.to_dict(),
            message = "Hotel created successfully"
        )

    async def get_my_hotels(self, partner_id: str, page: int, limit: int):
        hotels, total = await self.repo.get_partner_hotels(self.db, partner_id, page, limit)
        return list_response(
            data  = [h.to_dict() for h in hotels],
            total = total,
            page  = page,
            limit = limit
        )

    async def update_hotel(self, hotel_id: int, data: HotelUpdateSchema, partner_id: str):
        hotel = await self.get_owned_hotel(hotel_id, partner_id)
        hotel = await self.repo.update_hotel(self.db, hotel, data)
        return success_response(
            data    = hotel.to_dict(),
            message = "Hotel updated successfully"
        )

    async def delete_hotel(self, hotel_id: int, partner_id: str):
        hotel = await self.get_owned_hotel(hotel_id, partner_id)
        await self.repo.soft_delete_hotel(self.db, hotel)
        return success_response(message="Hotel deactivated successfully")

    # ─── Room CRUD ────────────────────────────────────────────

    async def add_room(self, hotel_id: int, data: RoomCreateSchema, partner_id: str):
        await self.get_owned_hotel(hotel_id, partner_id)
        room = await self.repo.create_room(self.db, hotel_id, data)
        return created_response(
            data    = room.to_dict(),
            message = "Room added successfully"
        )

    async def update_room(
        self, hotel_id: int, room_id: int,
        data: RoomUpdateSchema, partner_id: str
    ):
        await self.get_owned_hotel(hotel_id, partner_id)
        room = await self.repo.get_room_by_id(self.db, hotel_id, room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        room = await self.repo.update_room(self.db, room, data)
        return success_response(
            data    = room.to_dict(),
            message = "Room updated successfully"
        )

    async def delete_room(self, hotel_id: int, room_id: int, partner_id: str):
        await self.get_owned_hotel(hotel_id, partner_id)
        room = await self.repo.get_room_by_id(self.db, hotel_id, room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        await self.repo.delete_room(self.db, room)
        return success_response(message="Room removed successfully")

    async def update_room_pricing(
        self, hotel_id: int, room_id: int,
        data: RoomPricingSchema, partner_id: str
    ):
        await self.get_owned_hotel(hotel_id, partner_id)
        room = await self.repo.get_room_by_id(self.db, hotel_id, room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        room = await self.repo.update_room_pricing(self.db, room, data.price_per_night)
        return success_response(
            data    = room.to_dict(),
            message = f"Room price updated to Rs.{data.price_per_night}"
        )

    async def toggle_room_availability(
        self, hotel_id: int, room_id: int,
        data: RoomAvailabilitySchema, partner_id: str
    ):
        await self.get_owned_hotel(hotel_id, partner_id)
        room = await self.repo.get_room_by_id(self.db, hotel_id, room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        room = await self.repo.toggle_room_availability(self.db, room, data.is_active)
        status = "active" if data.is_active else "inactive"
        return success_response(
            data    = room.to_dict(),
            message = f"Room is now {status}"
        )

    async def block_room_dates(
        self, hotel_id: int, room_id: int,
        data: RoomBlockSchema, partner_id: str
    ):
        await self.get_owned_hotel(hotel_id, partner_id)
        room = await self.repo.get_room_by_id(self.db, hotel_id, room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        blocks = await self.repo.block_room_dates(
            self.db, room.id, data.block_dates, data.reason
        )
        return success_response(
            data    = {"blocked_dates": data.block_dates, "count": len(blocks)},
            message = f"{len(blocks)} date(s) blocked successfully"
        )

    # ─── Images ───────────────────────────────────────────────

    async def upload_image(self, hotel_id: int, file: UploadFile, partner_id: str):
        hotel = await self.get_owned_hotel(hotel_id, partner_id)

        if file.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=400,
                detail="Only JPG, PNG and WEBP images are allowed"
            )

        contents = await file.read()
        if len(contents) > MAX_IMAGE_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail=f"Image size must be less than {MAX_IMAGE_SIZE_MB}MB"
            )

        file_ext  = file.filename.split(".")[-1]
        file_name = f"{uuid.uuid4()}.{file_ext}"
        file_path = os.path.join(settings.UPLOAD_DIR, file_name)
        image_url = f"/uploads/hotels/{file_name}"

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(contents)

        hotel = await self.repo.add_image(self.db, hotel, image_url)
        return created_response(
            data    = {"image_url": image_url, "images": hotel.images},
            message = "Image uploaded successfully"
        )

    async def delete_image(self, hotel_id: int, image_id: str, partner_id: str):
        hotel = await self.get_owned_hotel(hotel_id, partner_id)
        hotel = await self.repo.delete_image(self.db, hotel, image_id)
        return success_response(
            data    = {"images": hotel.images},
            message = "Image deleted successfully"
        )

    # ─── Amenities ────────────────────────────────────────────

    async def add_amenity(self, hotel_id: int, data: AmenityAddSchema, partner_id: str):
        hotel = await self.get_owned_hotel(hotel_id, partner_id)
        hotel = await self.repo.add_amenity(self.db, hotel, data.amenity)
        return success_response(
            data    = {"amenities": hotel.amenities},
            message = f"Amenity '{data.amenity}' added successfully"
        )

    async def delete_amenity(self, hotel_id: int, amenity_id: int, partner_id: str):
        hotel = await self.get_owned_hotel(hotel_id, partner_id)
        hotel = await self.repo.delete_amenity(self.db, hotel, amenity_id)
        return success_response(
            data    = {"amenities": hotel.amenities},
            message = "Amenity removed successfully"
        )