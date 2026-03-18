from fastapi import APIRouter, Depends, Query, Path, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.deps.database import get_db
from uuid import UUID
from src.services.hotel_service import HotelPartnerService
from src.schemas.hotel import (
    HotelCreateSchema, HotelUpdateSchema,
    RoomCreateSchema, RoomUpdateSchema,
    RoomPricingSchema, RoomAvailabilitySchema,
    RoomBlockSchema, AmenityAddSchema
)

router = APIRouter()

DUMMY_PARTNER = "00000000-0000-0000-0000-000000000000"


def get_hotel_service(db: AsyncSession = Depends(get_db)) -> HotelPartnerService:
    return HotelPartnerService(db)


@router.get("/my-hotels", summary="Get all my hotels")
async def get_my_hotels(
    page:    int                 = Query(1,  ge=1),
    limit:   int                 = Query(20, ge=1, le=100),
    service: HotelPartnerService = Depends(get_hotel_service)
):
    return await service.get_my_hotels(DUMMY_PARTNER, page, limit)


@router.post("/", summary="Create hotel listing")
async def create_hotel(
    data:    HotelCreateSchema   = ...,
    service: HotelPartnerService = Depends(get_hotel_service)
):
    return await service.create_hotel(data, DUMMY_PARTNER)


@router.put("/{hotel_id}", summary="Update hotel details")
async def update_hotel(
    hotel_id: UUID               = Path(..., description="Hotel ID"),
    data:     HotelUpdateSchema  = ...,
    service:  HotelPartnerService = Depends(get_hotel_service)
):
    return await service.update_hotel(hotel_id, data, DUMMY_PARTNER)


@router.delete("/{hotel_id}", summary="Deactivate hotel")
async def delete_hotel(
    hotel_id: UUID               = Path(..., description="Hotel ID"),
    service:  HotelPartnerService = Depends(get_hotel_service)
):
    return await service.delete_hotel(hotel_id, DUMMY_PARTNER)


@router.post("/{hotel_id}/rooms", summary="Add room type")
async def add_room(
    hotel_id: UUID               = Path(..., description="Hotel ID"),
    data:     RoomCreateSchema   = ...,
    service:  HotelPartnerService = Depends(get_hotel_service)
):
    return await service.add_room(hotel_id, data, DUMMY_PARTNER)


@router.put("/{hotel_id}/rooms/{room_id}", summary="Update room details")
async def update_room(
    hotel_id: UUID               = Path(..., description="Hotel ID"),
    room_id:  UUID               = Path(..., description="Room ID"),
    data:     RoomUpdateSchema   = ...,
    service:  HotelPartnerService = Depends(get_hotel_service)
):
    return await service.update_room(hotel_id, room_id, data, DUMMY_PARTNER)


@router.delete("/{hotel_id}/rooms/{room_id}", summary="Remove room type")
async def delete_room(
    hotel_id: UUID               = Path(..., description="Hotel ID"),
    room_id:  UUID               = Path(..., description="Room ID"),
    service:  HotelPartnerService = Depends(get_hotel_service)
):
    return await service.delete_room(hotel_id, room_id, DUMMY_PARTNER)


@router.put("/{hotel_id}/rooms/{room_id}/pricing", summary="Update room price")
async def update_room_pricing(
    hotel_id: UUID               = Path(..., description="Hotel ID"),
    room_id:  UUID               = Path(..., description="Room ID"),
    data:     RoomPricingSchema  = ...,
    service:  HotelPartnerService = Depends(get_hotel_service)
):
    return await service.update_room_pricing(hotel_id, room_id, data, DUMMY_PARTNER)


@router.put("/{hotel_id}/rooms/{room_id}/availability", summary="Toggle room availability")
async def toggle_room_availability(
    hotel_id: UUID                    = Path(..., description="Hotel ID"),
    room_id:  UUID                    = Path(..., description="Room ID"),
    data:     RoomAvailabilitySchema = ...,
    service:  HotelPartnerService    = Depends(get_hotel_service)
):
    return await service.toggle_room_availability(hotel_id, room_id, data, DUMMY_PARTNER)


@router.post("/{hotel_id}/rooms/{room_id}/block", summary="Block room dates")
async def block_room_dates(
    hotel_id: UUID                = Path(..., description="Hotel ID"),
    room_id:  UUID                = Path(..., description="Room ID"),
    data:     RoomBlockSchema    = ...,
    service:  HotelPartnerService = Depends(get_hotel_service)
):
    return await service.block_room_dates(hotel_id, room_id, data, DUMMY_PARTNER)


@router.post("/{hotel_id}/images", summary="Upload hotel image")
async def upload_image(
    hotel_id: UUID               = Path(..., description="Hotel ID"),
    file:     UploadFile         = File(..., description="Image file (JPG/PNG/WEBP, max 5MB)"),
    service:  HotelPartnerService = Depends(get_hotel_service)
):
    return await service.upload_image(hotel_id, file, DUMMY_PARTNER)


@router.delete("/{hotel_id}/images/{image_id}", summary="Delete hotel image")
async def delete_image(
    hotel_id: UUID               = Path(..., description="Hotel ID"),
    image_id: UUID               = Path(..., description="Image UUID"),
    service:  HotelPartnerService = Depends(get_hotel_service)
):
    return await service.delete_image(hotel_id, image_id, DUMMY_PARTNER)


@router.post("/{hotel_id}/amenities", summary="Add hotel amenity")
async def add_amenity(
    hotel_id: UUID               = Path(..., description="Hotel ID"),
    data:     AmenityAddSchema   = ...,
    service:  HotelPartnerService = Depends(get_hotel_service)
):
    return await service.add_amenity(hotel_id, data, DUMMY_PARTNER)


@router.delete("/{hotel_id}/amenities/{amenity_id}", summary="Remove hotel amenity")
async def delete_amenity(
    hotel_id:   UUID             = Path(..., description="Hotel ID"),
    amenity_id: UUID             = Path(..., description="Amenity index (0-based)"),
    service:    HotelPartnerService = Depends(get_hotel_service)
):
    return await service.delete_amenity(hotel_id, amenity_id, DUMMY_PARTNER)
