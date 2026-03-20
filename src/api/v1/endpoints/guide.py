import logging
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, Query
from sqlalchemy.orm import Session

from src.api.deps.database import get_db
from src.schemas.guide import (
    GuideCreateSchema, GuideUpdateSchema, GuideStatusUpdateSchema,
    GuideLanguageCreateSchema, GuideSpecializationCreateSchema,
    GuideAvailabilityUpdateSchema, GuideResponseSchema
)
import src.services.guide_service as guide_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/guides", tags=["Guides"])


async def success(data, message: str = "") -> dict:
    return {"success": True, "data": data, "message": message}


# NOTE: user_id=1 is temporary until LEV148 completes auth module


# ─── Public Endpoints ─────────────────────────────────────────────────────────

@router.get("/")
async def list_guides(
    city: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    specialization: Optional[str] = Query(None),
    min_rating: Optional[float] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db)
):
    result = await guide_service.list_guides(db, city, language, specialization, min_rating, page, limit)
    return success(result)


@router.get("/featured")
async def get_featured_guides(db: Session = Depends(get_db)):
    result = await guide_service.get_featured_guides(db)
    return success(result)


@router.get("/by-language/{language}")
async def get_guides_by_language(
    language: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db)
):
    result = await guide_service.get_guides_by_language(db, language, page, limit)
    return success(result)


@router.get("/by-specialization/{specialization}")
async def get_guides_by_specialization(
    specialization: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db)
):
    result = await guide_service.get_guides_by_specialization(db, specialization, page, limit)
    return success(result)


@router.get("/by-location/{city}")
async def get_guides_by_location(
    city: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db)
):
    result = await guide_service.get_guides_by_location(db, city, page, limit)
    return success(result)


@router.get("/{guide_id}")
async def get_guide_detail(
    guide_id: int,
    db: Session = Depends(get_db)
):
    result = await guide_service.get_guide_detail(db, guide_id)
    return success(result)


@router.get("/{guide_id}/reviews")
async def get_guide_reviews(
    guide_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db)
):
    result = await guide_service.get_guide_reviews(db, guide_id, page, limit)
    return success(result)


@router.get("/{guide_id}/availability")
async def get_guide_availability(
    guide_id: int,
    db: Session = Depends(get_db)
):
    result = await guide_service.get_guide_availability(db, guide_id)
    return success(result)


# ─── Protected Endpoints ──────────────────────────────────────────────────────

@router.post("/")
async def register_guide(
    data: GuideCreateSchema,
    db: Session = Depends(get_db)
):
    result = await guide_service.register_guide(db, 1, data)
    return success(GuideResponseSchema.from_orm(result), "Guide registered successfully")


@router.put("/{guide_id}")
async def update_guide(
    guide_id: int,
    data: GuideUpdateSchema,
    db: Session = Depends(get_db)
):
    result = await guide_service.update_guide(db, guide_id, 1, data)
    return success(GuideResponseSchema.from_orm(result), "Guide updated")


@router.put("/{guide_id}/status")
async def update_guide_status(
    guide_id: int,
    data: GuideStatusUpdateSchema,
    db: Session = Depends(get_db)
):
    result = await guide_service.update_guide_status(db, guide_id, 1, data)
    return success(GuideResponseSchema.from_orm(result), "Status updated")


@router.put("/{guide_id}/availability")
async def update_guide_availability(
    guide_id: int,
    data: GuideAvailabilityUpdateSchema,
    db: Session = Depends(get_db)
):
    result = await guide_service.update_guide_availability(db, guide_id, 1, data)
    return success({"unavailable_dates": result.unavailable_dates}, "Availability updated")


# ─── Languages ────────────────────────────────────────────────────────────────

@router.post("/{guide_id}/languages")
async def add_language(
    guide_id: int,
    data: GuideLanguageCreateSchema,
    db: Session = Depends(get_db)
):
    result = await guide_service.add_language(db, guide_id, 1, data)
    return success(result, "Language added")


@router.delete("/{guide_id}/languages/{language_id}")
async def remove_language(
    guide_id: int,
    language_id: int,
    db: Session = Depends(get_db)
):
    result = await guide_service.remove_language(db, guide_id, language_id, 1)
    return success(result)


# ─── Specializations ──────────────────────────────────────────────────────────

@router.post("/{guide_id}/specializations")
async def add_specialization(
    guide_id: int,
    data: GuideSpecializationCreateSchema,
    db: Session = Depends(get_db)
):
    result = await guide_service.add_specialization(db, guide_id, 1, data)
    return success(result, "Specialization added")


@router.delete("/{guide_id}/specializations/{spec_id}")
async def remove_specialization(
    guide_id: int,
    spec_id: int,
    db: Session = Depends(get_db)
):
    result = await guide_service.remove_specialization(db, guide_id, spec_id, 1)
    return success(result)


# ─── Documents ────────────────────────────────────────────────────────────────

@router.post("/{guide_id}/documents")
async def upload_document(
    guide_id: int,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    file_url = f"https://s3.amazonaws.com/ap-tourism/guide-documents/{file.filename}"
    result = await guide_service.upload_document(db, guide_id, 1, document_type, file_url)
    return success(result, "Document uploaded")


# ─── Bookings ─────────────────────────────────────────────────────────────────

@router.get("/{guide_id}/bookings")
async def get_guide_bookings(
    guide_id: int,
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db)
):
    result = await guide_service.get_guide_bookings(db, guide_id, 1, status, page, limit)
    return success(result)
