"""
services/guide_service.py
Guide module — fixed for LEV146 integration.
Changes:
  - sync Session → async AsyncSession
  - db.query() → await db.execute(select())
  - .dict() → .model_dump()
  - UUID primary keys
"""

from uuid import UUID
from typing import Optional
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models.guide import (
    Guide, GuideLanguage, GuideSpecialization, GuideDocument, GuideStatus
)
from src.schemas.guide import (
    GuideCreateSchema, GuideUpdateSchema, GuideStatusUpdateSchema,
    GuideLanguageCreateSchema, GuideSpecializationCreateSchema,
    GuideAvailabilityUpdateSchema
)


# ─── Helpers ──────────────────────────────────────────────────

async def get_guide_by_id(db: AsyncSession, guide_id: UUID) -> Guide:
    result = await db.execute(
        select(Guide).where(Guide.id == guide_id, Guide.deleted_at.is_(None))
    )
    guide = result.scalar_one_or_none()
    if not guide:
        raise HTTPException(status_code=404, detail="Guide not found")
    return guide


async def get_guide_by_user_id(db: AsyncSession, user_id: UUID) -> Guide:
    result = await db.execute(
        select(Guide).where(Guide.user_id == user_id, Guide.deleted_at.is_(None))
    )
    guide = result.scalar_one_or_none()
    if not guide:
        raise HTTPException(status_code=404, detail="Guide profile not found")
    return guide


def _guide_to_dict(guide: Guide) -> dict:
    return {
        "id":                 str(guide.id),
        "user_id":            str(guide.user_id),
        "full_name":          guide.full_name,
        "bio":                guide.bio,
        "profile_photo":      guide.profile_photo,
        "city":               guide.city,
        "state":              guide.state,
        "experience_years":   guide.experience_years,
        "rating":             guide.rating,
        "total_reviews":      guide.total_reviews,
        "total_trips":        guide.total_trips,
        "status":             guide.status.value if guide.status else None,
        "is_featured":        guide.is_featured,
        "is_verified":        guide.is_verified,
        "price_per_day":      guide.price_per_day,
        "price_per_half_day": guide.price_per_half_day,
        "certifications":     guide.certifications or [],
        "destinations":       guide.destinations or [],
        "unavailable_dates":  guide.unavailable_dates or [],
        "created_at":         guide.created_at,
    }


# ─── Public ───────────────────────────────────────────────────

async def list_guides(
    db: AsyncSession,
    city: str = None,
    language: str = None,
    specialization: str = None,
    min_rating: float = None,
    page: int = 1,
    limit: int = 20
) -> dict:
    from sqlalchemy import func
    query = select(Guide).where(
        Guide.status == GuideStatus.ACTIVE,
        Guide.deleted_at.is_(None)
    )
    if city:
        query = query.where(Guide.city.ilike(f"%{city}%"))
    if min_rating:
        query = query.where(Guide.rating >= min_rating)
    if language:
        query = query.join(GuideLanguage).where(
            GuideLanguage.language.ilike(f"%{language}%")
        )
    if specialization:
        query = query.join(GuideSpecialization).where(
            GuideSpecialization.specialization == specialization
        )

    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar()

    result = await db.execute(query.offset((page - 1) * limit).limit(limit))
    guides = result.scalars().all()

    return {
        "data":  [_guide_to_dict(g) for g in guides],
        "total": total,
        "page":  page,
        "pages": -(-total // limit) if total else 0,
    }


async def get_featured_guides(db: AsyncSession) -> list:
    result = await db.execute(
        select(Guide).where(
            Guide.is_featured == True,
            Guide.status == GuideStatus.ACTIVE,
            Guide.deleted_at.is_(None)
        ).order_by(Guide.rating.desc()).limit(10)
    )
    guides = result.scalars().all()
    return [_guide_to_dict(g) for g in guides]


async def get_guides_by_language(db: AsyncSession, language: str, page: int, limit: int) -> list:
    result = await db.execute(
        select(Guide).join(GuideLanguage).where(
            GuideLanguage.language.ilike(f"%{language}%"),
            Guide.status == GuideStatus.ACTIVE,
            Guide.deleted_at.is_(None)
        ).offset((page - 1) * limit).limit(limit)
    )
    guides = result.scalars().all()
    return [_guide_to_dict(g) for g in guides]


async def get_guides_by_specialization(db: AsyncSession, specialization: str, page: int, limit: int) -> list:
    result = await db.execute(
        select(Guide).join(GuideSpecialization).where(
            GuideSpecialization.specialization == specialization,
            Guide.status == GuideStatus.ACTIVE,
            Guide.deleted_at.is_(None)
        ).offset((page - 1) * limit).limit(limit)
    )
    guides = result.scalars().all()
    return [_guide_to_dict(g) for g in guides]


async def get_guides_by_location(db: AsyncSession, city: str, page: int, limit: int) -> list:
    result = await db.execute(
        select(Guide).where(
            Guide.city.ilike(f"%{city}%"),
            Guide.status == GuideStatus.ACTIVE,
            Guide.deleted_at.is_(None)
        ).offset((page - 1) * limit).limit(limit)
    )
    guides = result.scalars().all()
    return [_guide_to_dict(g) for g in guides]


async def get_guide_detail(db: AsyncSession, guide_id: UUID) -> dict:
    guide = await get_guide_by_id(db, guide_id)
    return _guide_to_dict(guide)


async def get_guide_reviews(db: AsyncSession, guide_id: UUID, page: int, limit: int) -> dict:
    await get_guide_by_id(db, guide_id)
    return {"data": [], "total": 0, "page": page, "pages": 0}


async def get_guide_availability(db: AsyncSession, guide_id: UUID) -> dict:
    guide = await get_guide_by_id(db, guide_id)
    return {"unavailable_dates": guide.unavailable_dates or []}


# ─── Protected ────────────────────────────────────────────────

async def register_guide(db: AsyncSession, user_id: UUID, data: GuideCreateSchema) -> dict:
    result = await db.execute(select(Guide).where(Guide.user_id == user_id))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Guide profile already exists")

    guide = Guide(
        user_id=user_id,
        full_name=data.full_name,
        bio=data.bio,
        city=data.city,
        state=data.state,
        experience_years=data.experience_years,
        price_per_day=data.price_per_day,
        price_per_half_day=data.price_per_half_day,
        certifications=data.certifications or [],
        destinations=data.destinations or [],
    )
    db.add(guide)
    await db.commit()
    await db.refresh(guide)
    return _guide_to_dict(guide)


async def update_guide(db: AsyncSession, guide_id: UUID, user_id: UUID, data: GuideUpdateSchema) -> dict:
    guide = await get_guide_by_id(db, guide_id)
    if str(guide.user_id) != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized")
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(guide, field, value)
    await db.commit()
    await db.refresh(guide)
    return _guide_to_dict(guide)


async def update_guide_status(db: AsyncSession, guide_id: UUID, user_id: UUID, data: GuideStatusUpdateSchema) -> dict:
    guide = await get_guide_by_id(db, guide_id)
    if str(guide.user_id) != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized")
    guide.status = data.status
    await db.commit()
    await db.refresh(guide)
    return _guide_to_dict(guide)


async def update_guide_availability(db: AsyncSession, guide_id: UUID, user_id: UUID, data: GuideAvailabilityUpdateSchema) -> dict:
    guide = await get_guide_by_id(db, guide_id)
    if str(guide.user_id) != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized")
    guide.unavailable_dates = data.unavailable_dates
    await db.commit()
    return {"unavailable_dates": guide.unavailable_dates}


# ─── Languages ────────────────────────────────────────────────

async def add_language(db: AsyncSession, guide_id: UUID, user_id: UUID, data: GuideLanguageCreateSchema) -> dict:
    guide = await get_guide_by_id(db, guide_id)
    if str(guide.user_id) != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    result = await db.execute(
        select(GuideLanguage).where(
            GuideLanguage.guide_id == guide_id,
            GuideLanguage.language == data.language
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Language already added")

    lang = GuideLanguage(guide_id=guide_id, language=data.language, proficiency=data.proficiency)
    db.add(lang)
    await db.commit()
    await db.refresh(lang)
    return {"id": str(lang.id), "language": lang.language, "proficiency": lang.proficiency.value}


async def remove_language(db: AsyncSession, guide_id: UUID, language_id: UUID, user_id: UUID) -> dict:
    guide = await get_guide_by_id(db, guide_id)
    if str(guide.user_id) != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    result = await db.execute(
        select(GuideLanguage).where(
            GuideLanguage.id == language_id,
            GuideLanguage.guide_id == guide_id
        )
    )
    lang = result.scalar_one_or_none()
    if not lang:
        raise HTTPException(status_code=404, detail="Language not found")

    await db.delete(lang)
    await db.commit()
    return {"message": "Language removed"}


# ─── Specializations ──────────────────────────────────────────

async def add_specialization(db: AsyncSession, guide_id: UUID, user_id: UUID, data: GuideSpecializationCreateSchema) -> dict:
    guide = await get_guide_by_id(db, guide_id)
    if str(guide.user_id) != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    result = await db.execute(
        select(GuideSpecialization).where(
            GuideSpecialization.guide_id == guide_id,
            GuideSpecialization.specialization == data.specialization
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Specialization already added")

    spec = GuideSpecialization(guide_id=guide_id, specialization=data.specialization)
    db.add(spec)
    await db.commit()
    await db.refresh(spec)
    return {"id": str(spec.id), "specialization": spec.specialization.value}


async def remove_specialization(db: AsyncSession, guide_id: UUID, spec_id: UUID, user_id: UUID) -> dict:
    guide = await get_guide_by_id(db, guide_id)
    if str(guide.user_id) != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    result = await db.execute(
        select(GuideSpecialization).where(
            GuideSpecialization.id == spec_id,
            GuideSpecialization.guide_id == guide_id
        )
    )
    spec = result.scalar_one_or_none()
    if not spec:
        raise HTTPException(status_code=404, detail="Specialization not found")

    await db.delete(spec)
    await db.commit()
    return {"message": "Specialization removed"}


# ─── Documents ────────────────────────────────────────────────

async def upload_document(db: AsyncSession, guide_id: UUID, user_id: UUID, document_type: str, file_url: str) -> dict:
    guide = await get_guide_by_id(db, guide_id)
    if str(guide.user_id) != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    doc = GuideDocument(guide_id=guide_id, document_type=document_type, file_url=file_url)
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return {"id": str(doc.id), "document_type": doc.document_type, "file_url": doc.file_url}


# ─── Bookings ─────────────────────────────────────────────────

async def get_guide_bookings(db: AsyncSession, guide_id: UUID, user_id: UUID, status: str = None, page: int = 1, limit: int = 20) -> dict:
    guide = await get_guide_by_id(db, guide_id)
    if str(guide.user_id) != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized")
    return {"data": [], "total": 0, "page": page, "pages": 0}