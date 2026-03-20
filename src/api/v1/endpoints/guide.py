"""
api/v1/endpoints/guide.py
Guide module — all endpoints using LEV146 patterns.

Public:
  GET  /guides/                          — List guides with filters
  GET  /guides/featured                  — Featured guides
  GET  /guides/by-language/{language}    — Guides by language
  GET  /guides/by-specialization/{spec}  — Guides by specialization
  GET  /guides/by-location/{city}        — Guides by city
  GET  /guides/{guide_id}                — Guide detail
  GET  /guides/{guide_id}/reviews        — Guide reviews
  GET  /guides/{guide_id}/availability   — Unavailable dates

Protected:
  POST   /guides/                                    — Register guide profile
  PUT    /guides/{guide_id}                          — Update guide
  PUT    /guides/{guide_id}/status                   — Update status
  PUT    /guides/{guide_id}/availability             — Update unavailable dates
  POST   /guides/{guide_id}/languages                — Add language
  DELETE /guides/{guide_id}/languages/{language_id}  — Remove language
  POST   /guides/{guide_id}/specializations          — Add specialization
  DELETE /guides/{guide_id}/specializations/{spec_id} — Remove specialization
  POST   /guides/{guide_id}/documents                — Upload document
  GET    /guides/{guide_id}/bookings                 — Guide bookings
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, UploadFile, File, Form, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.api.deps.auth import get_current_user
from src.models.user import User
from src.schemas.guide import (
    GuideCreateSchema, GuideUpdateSchema, GuideStatusUpdateSchema,
    GuideLanguageCreateSchema, GuideSpecializationCreateSchema,
    GuideAvailabilityUpdateSchema,
)
from src.common.responses import APIResponse
import src.services.guide_service as guide_service

router = APIRouter(prefix="/guides", tags=["Guides"])


# ══════════════════════════════════════════════════════════════
# PUBLIC ENDPOINTS
# Static routes MUST come before /{guide_id}
# ══════════════════════════════════════════════════════════════

@router.get("/featured", response_model=APIResponse, summary="Featured guides")
async def get_featured_guides(db: AsyncSession = Depends(get_db)):
    data = await guide_service.get_featured_guides(db)
    return APIResponse.success(message=f"{len(data)} featured guides", data=data)


@router.get("/by-language/{language}", response_model=APIResponse, summary="Guides by language")
async def get_guides_by_language(
    language: str,
    page:  int = Query(1, ge=1),
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
):
    data = await guide_service.get_guides_by_language(db, language, page, limit)
    return APIResponse.success(message=f"Guides speaking {language}", data=data)


@router.get("/by-specialization/{specialization}", response_model=APIResponse, summary="Guides by specialization")
async def get_guides_by_specialization(
    specialization: str,
    page:  int = Query(1, ge=1),
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
):
    data = await guide_service.get_guides_by_specialization(db, specialization, page, limit)
    return APIResponse.success(message=f"Guides for {specialization}", data=data)


@router.get("/by-location/{city}", response_model=APIResponse, summary="Guides by city")
async def get_guides_by_location(
    city:  str,
    page:  int = Query(1, ge=1),
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
):
    data = await guide_service.get_guides_by_location(db, city, page, limit)
    return APIResponse.success(message=f"Guides in {city}", data=data)


@router.get("", response_model=APIResponse, summary="List guides with filters")
async def list_guides(
    city:           Optional[str]   = Query(None),
    language:       Optional[str]   = Query(None),
    specialization: Optional[str]   = Query(None),
    min_rating:     Optional[float] = Query(None),
    page:           int             = Query(1, ge=1),
    limit:          int             = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
):
    result = await guide_service.list_guides(db, city, language, specialization, min_rating, page, limit)
    return APIResponse.success(message=f"{result['total']} guides found", data=result)


@router.get("/{guide_id}/reviews", response_model=APIResponse, summary="Guide reviews")
async def get_guide_reviews(
    guide_id: UUID,
    page:  int = Query(1, ge=1),
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
):
    result = await guide_service.get_guide_reviews(db, guide_id, page, limit)
    return APIResponse.success(message="Reviews fetched", data=result)


@router.get("/{guide_id}/availability", response_model=APIResponse, summary="Guide availability")
async def get_guide_availability(
    guide_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await guide_service.get_guide_availability(db, guide_id)
    return APIResponse.success(message="Availability fetched", data=result)


@router.get("/{guide_id}", response_model=APIResponse, summary="Guide detail")
async def get_guide_detail(
    guide_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await guide_service.get_guide_detail(db, guide_id)
    return APIResponse.success(message="Guide fetched", data=result)


# ══════════════════════════════════════════════════════════════
# PROTECTED ENDPOINTS
# ══════════════════════════════════════════════════════════════

@router.post("", response_model=APIResponse, status_code=201, summary="Register guide profile")
async def register_guide(
    data: GuideCreateSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await guide_service.register_guide(db, current_user.id, data)
    return APIResponse.success(message="Guide registered successfully", data=result)


@router.put("/{guide_id}", response_model=APIResponse, summary="Update guide profile")
async def update_guide(
    guide_id: UUID,
    data: GuideUpdateSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await guide_service.update_guide(db, guide_id, current_user.id, data)
    return APIResponse.success(message="Guide updated", data=result)


@router.put("/{guide_id}/status", response_model=APIResponse, summary="Update guide status")
async def update_guide_status(
    guide_id: UUID,
    data: GuideStatusUpdateSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await guide_service.update_guide_status(db, guide_id, current_user.id, data)
    return APIResponse.success(message="Status updated", data=result)


@router.put("/{guide_id}/availability", response_model=APIResponse, summary="Update unavailable dates")
async def update_guide_availability(
    guide_id: UUID,
    data: GuideAvailabilityUpdateSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await guide_service.update_guide_availability(db, guide_id, current_user.id, data)
    return APIResponse.success(message="Availability updated", data=result)


@router.post("/{guide_id}/languages", response_model=APIResponse, status_code=201, summary="Add language")
async def add_language(
    guide_id: UUID,
    data: GuideLanguageCreateSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await guide_service.add_language(db, guide_id, current_user.id, data)
    return APIResponse.success(message="Language added", data=result)


@router.delete("/{guide_id}/languages/{language_id}", response_model=APIResponse, summary="Remove language")
async def remove_language(
    guide_id:    UUID,
    language_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await guide_service.remove_language(db, guide_id, language_id, current_user.id)
    return APIResponse.success(message=result["message"])


@router.post("/{guide_id}/specializations", response_model=APIResponse, status_code=201, summary="Add specialization")
async def add_specialization(
    guide_id: UUID,
    data: GuideSpecializationCreateSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await guide_service.add_specialization(db, guide_id, current_user.id, data)
    return APIResponse.success(message="Specialization added", data=result)


@router.delete("/{guide_id}/specializations/{spec_id}", response_model=APIResponse, summary="Remove specialization")
async def remove_specialization(
    guide_id: UUID,
    spec_id:  UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await guide_service.remove_specialization(db, guide_id, spec_id, current_user.id)
    return APIResponse.success(message=result["message"])


@router.post("/{guide_id}/documents", response_model=APIResponse, status_code=201, summary="Upload document")
async def upload_document(
    guide_id:      UUID,
    document_type: str        = Form(...),
    file:          UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    file_url = f"https://ap-tourism-media.s3.ap-south-1.amazonaws.com/guides/{guide_id}/docs/{file.filename}"
    result = await guide_service.upload_document(db, guide_id, current_user.id, document_type, file_url)
    return APIResponse.success(message="Document uploaded", data=result)


@router.get("/{guide_id}/bookings", response_model=APIResponse, summary="Guide bookings")
async def get_guide_bookings(
    guide_id: UUID,
    status:   Optional[str] = Query(None),
    page:     int           = Query(1, ge=1),
    limit:    int           = Query(20, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await guide_service.get_guide_bookings(db, guide_id, current_user.id, status, page, limit)
    return APIResponse.success(message="Bookings fetched", data=result)