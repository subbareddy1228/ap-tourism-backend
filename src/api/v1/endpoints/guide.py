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


# ─── Helper ───────────────────────────────────────────────────────────────────

def success(data, message: str = "") -> dict:
    return {"success": True, "data": data, "message": message}


# NOTE: user_id=1 is temporary until LEV148 completes auth module
# After auth is ready, replace all user_id=1 with user.id from JWT token


# ─── Public Endpoints ─────────────────────────────────────────────────────────

@router.get("/")
def list_guides(
    city: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    specialization: Optional[str] = Query(None),
    min_rating: Optional[float] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db)
):
    """List all guides with filters: city, language, specialization, rating."""
    result = guide_service.list_guides(db, city, language, specialization, min_rating, page, limit)
    return success(result)


@router.get("/featured")
def get_featured_guides(db: Session = Depends(get_db)):
    """Top rated featured guides."""
    result = guide_service.get_featured_guides(db)
    return success(result)


@router.get("/by-language/{language}")
def get_guides_by_language(
    language: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db)
):
    """Filter guides by language: Telugu, Hindi, English, Tamil, Kannada."""
    result = guide_service.get_guides_by_language(db, language, page, limit)
    return success(result)


@router.get("/by-specialization/{specialization}")
def get_guides_by_specialization(
    specialization: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db)
):
    """Filter guides by specialization: TEMPLE, ADVENTURE, HERITAGE, ECO_TOURISM."""
    result = guide_service.get_guides_by_specialization(db, specialization, page, limit)
    return success(result)


@router.get("/by-location/{city}")
def get_guides_by_location(
    city: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db)
):
    """Get guides available in a specific city."""
    result = guide_service.get_guides_by_location(db, city, page, limit)
    return success(result)


@router.get("/{guide_id}")
def get_guide_detail(
    guide_id: int,
    db: Session = Depends(get_db)
):
    """Full guide profile: bio, languages, certifications, destinations, rating."""
    result = guide_service.get_guide_detail(db, guide_id)
    return success(result)


@router.get("/{guide_id}/reviews")
def get_guide_reviews(
    guide_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db)
):
    """Reviews received by a guide."""
    result = guide_service.get_guide_reviews(db, guide_id, page, limit)
    return success(result)


@router.get("/{guide_id}/availability")
def get_guide_availability(
    guide_id: int,
    db: Session = Depends(get_db)
):
    """Check guide availability — returns unavailable dates."""
    result = guide_service.get_guide_availability(db, guide_id)
    return success(result)


# ─── Protected Endpoints ──────────────────────────────────────────────────────

@router.post("/")
def register_guide(
    data: GuideCreateSchema,
    db: Session = Depends(get_db)
):
    """Register as guide."""
    result = guide_service.register_guide(db, 1, data)
    return success(GuideResponseSchema.from_orm(result), "Guide registered successfully")


@router.put("/{guide_id}")
def update_guide(
    guide_id: int,
    data: GuideUpdateSchema,
    db: Session = Depends(get_db)
):
    """Update guide profile."""
    result = guide_service.update_guide(db, guide_id, 1, data)
    return success(GuideResponseSchema.from_orm(result), "Guide updated")


@router.put("/{guide_id}/status")
def update_guide_status(
    guide_id: int,
    data: GuideStatusUpdateSchema,
    db: Session = Depends(get_db)
):
    """Update guide status: ACTIVE, INACTIVE, SUSPENDED."""
    result = guide_service.update_guide_status(db, guide_id, 1, data)
    return success(GuideResponseSchema.from_orm(result), "Status updated")


@router.put("/{guide_id}/availability")
def update_guide_availability(
    guide_id: int,
    data: GuideAvailabilityUpdateSchema,
    db: Session = Depends(get_db)
):
    """Set unavailable dates on the guide calendar."""
    result = guide_service.update_guide_availability(db, guide_id, 1, data)
    return success({"unavailable_dates": result.unavailable_dates}, "Availability updated")


# ─── Languages ────────────────────────────────────────────────────────────────

@router.post("/{guide_id}/languages")
def add_language(
    guide_id: int,
    data: GuideLanguageCreateSchema,
    db: Session = Depends(get_db)
):
    """Add a language: Telugu, Hindi, English, Tamil, Kannada."""
    result = guide_service.add_language(db, guide_id, 1, data)
    return success(result, "Language added")


@router.delete("/{guide_id}/languages/{language_id}")
def remove_language(
    guide_id: int,
    language_id: int,
    db: Session = Depends(get_db)
):
    """Remove a language from guide profile."""
    result = guide_service.remove_language(db, guide_id, language_id, 1)
    return success(result)


# ─── Specializations ──────────────────────────────────────────────────────────

@router.post("/{guide_id}/specializations")
def add_specialization(
    guide_id: int,
    data: GuideSpecializationCreateSchema,
    db: Session = Depends(get_db)
):
    """Add specialization: TEMPLE, ADVENTURE, HERITAGE, ECO_TOURISM."""
    result = guide_service.add_specialization(db, guide_id, 1, data)
    return success(result, "Specialization added")


@router.delete("/{guide_id}/specializations/{spec_id}")
def remove_specialization(
    guide_id: int,
    spec_id: int,
    db: Session = Depends(get_db)
):
    """Remove a specialization from guide profile."""
    result = guide_service.remove_specialization(db, guide_id, spec_id, 1)
    return success(result)


# ─── Documents ────────────────────────────────────────────────────────────────

@router.post("/{guide_id}/documents")
def upload_document(
    guide_id: int,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload guide documents."""
    # TODO: upload to S3 using s3_utils
    file_url = f"https://s3.amazonaws.com/ap-tourism/guide-documents/{file.filename}"
    result = guide_service.upload_document(db, guide_id, 1, document_type, file_url)
    return success(result, "Document uploaded")


# ─── Bookings (READ ONLY) ─────────────────────────────────────────────────────

@router.get("/{guide_id}/bookings")
def get_guide_bookings(
    guide_id: int,
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db)
):
    """Guide's assigned trips: upcoming, active, completed."""
    result = guide_service.get_guide_bookings(db, guide_id, 1, status, page, limit)
    return success(result)
