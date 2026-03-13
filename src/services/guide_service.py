from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile
from typing import Optional, List

from src.models.guide import Guide, GuideLanguage, GuideSpecialization, GuideDocument, GuideStatus
from src.schemas.guide import (
    GuideCreateSchema, GuideUpdateSchema, GuideStatusUpdateSchema,
    GuideLanguageCreateSchema, GuideSpecializationCreateSchema,
    GuideAvailabilityUpdateSchema
)

# ─── Helper ───────────────────────────────────────────────────────────────────

def get_guide_by_id(db: Session, guide_id: int) -> Guide:
    guide = db.query(Guide).filter(
        Guide.id == guide_id,
        Guide.deleted_at == None
    ).first()
    if not guide:
        raise HTTPException(status_code=404, detail="Guide not found")
    return guide


def get_guide_by_user_id(db: Session, user_id: int) -> Guide:
    guide = db.query(Guide).filter(
        Guide.user_id == user_id,
        Guide.deleted_at == None
    ).first()
    if not guide:
        raise HTTPException(status_code=404, detail="Guide profile not found")
    return guide


# ─── Public Endpoints ─────────────────────────────────────────────────────────

def list_guides(db: Session, city: str = None, language: str = None,
                specialization: str = None, min_rating: float = None,
                page: int = 1, limit: int = 20) -> dict:
    query = db.query(Guide).filter(
        Guide.status == GuideStatus.ACTIVE,
        Guide.deleted_at == None
    )
    if city:
        query = query.filter(Guide.city.ilike(f"%{city}%"))
    if min_rating:
        query = query.filter(Guide.rating >= min_rating)
    if language:
        query = query.join(GuideLanguage).filter(GuideLanguage.language.ilike(f"%{language}%"))
    if specialization:
        query = query.join(GuideSpecialization).filter(GuideSpecialization.specialization == specialization)
    total = query.count()
    guides = query.offset((page - 1) * limit).limit(limit).all()
    return {"data": guides, "total": total, "page": page, "pages": -(-total // limit)}


def get_featured_guides(db: Session) -> list:
    return db.query(Guide).filter(
        Guide.is_featured == True,
        Guide.status == GuideStatus.ACTIVE,
        Guide.deleted_at == None
    ).order_by(Guide.rating.desc()).limit(10).all()


def get_guides_by_language(db: Session, language: str, page: int, limit: int) -> list:
    return db.query(Guide).join(GuideLanguage).filter(
        GuideLanguage.language.ilike(f"%{language}%"),
        Guide.status == GuideStatus.ACTIVE,
        Guide.deleted_at == None
    ).offset((page - 1) * limit).limit(limit).all()


def get_guides_by_specialization(db: Session, specialization: str, page: int, limit: int) -> list:
    return db.query(Guide).join(GuideSpecialization).filter(
        GuideSpecialization.specialization == specialization,
        Guide.status == GuideStatus.ACTIVE,
        Guide.deleted_at == None
    ).offset((page - 1) * limit).limit(limit).all()


def get_guides_by_location(db: Session, city: str, page: int, limit: int) -> list:
    return db.query(Guide).filter(
        Guide.city.ilike(f"%{city}%"),
        Guide.status == GuideStatus.ACTIVE,
        Guide.deleted_at == None
    ).offset((page - 1) * limit).limit(limit).all()


def get_guide_detail(db: Session, guide_id: int) -> Guide:
    return get_guide_by_id(db, guide_id)


def get_guide_reviews(db: Session, guide_id: int, page: int, limit: int) -> dict:
    get_guide_by_id(db, guide_id)
    # TODO: uncomment when Review module is ready
    # from src.models.review import Review
    # reviews = db.query(Review).filter(Review.entity_id == guide_id, Review.entity_type == "GUIDE")
    return {"data": [], "total": 0, "page": page, "pages": 0}


def get_guide_availability(db: Session, guide_id: int) -> dict:
    guide = get_guide_by_id(db, guide_id)
    return {"unavailable_dates": guide.unavailable_dates}


# ─── Partner/Guide Protected Endpoints ───────────────────────────────────────

def register_guide(db: Session, user_id: int, data: GuideCreateSchema) -> Guide:
    existing = db.query(Guide).filter(Guide.user_id == user_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Guide profile already exists")

    guide = Guide(
        #user_id=user_id,
        partner_id=1,       # temp until partner linking is ready
        full_name=data.full_name,
        bio=data.bio,
        city=data.city,
        state=data.state,
        experience_years=data.experience_years,
        price_per_day=data.price_per_day,
        price_per_half_day=data.price_per_half_day,
        certifications=data.certifications,
        destinations=data.destinations,
    )
    db.add(guide)
    db.commit()
    db.refresh(guide)
    return guide


def update_guide(db: Session, guide_id: int, user_id: int, data: GuideUpdateSchema) -> Guide:
    guide = get_guide_by_id(db, guide_id)
    if guide.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    update_data = data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(guide, field, value)
    db.commit()
    db.refresh(guide)
    return guide


def update_guide_status(db: Session, guide_id: int, user_id: int, data: GuideStatusUpdateSchema) -> Guide:
    guide = get_guide_by_id(db, guide_id)
    if guide.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    guide.status = data.status
    db.commit()
    db.refresh(guide)
    return guide


def update_guide_availability(db: Session, guide_id: int, user_id: int, data: GuideAvailabilityUpdateSchema) -> Guide:
    guide = get_guide_by_id(db, guide_id)
    if guide.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    guide.unavailable_dates = data.unavailable_dates
    db.commit()
    db.refresh(guide)
    return guide


# ─── Languages ────────────────────────────────────────────────────────────────

def add_language(db: Session, guide_id: int, user_id: int, data: GuideLanguageCreateSchema):
    guide = get_guide_by_id(db, guide_id)
    if guide.user_id != 1:
        raise HTTPException(status_code=403, detail="Not authorized")
    existing = db.query(GuideLanguage).filter(
        GuideLanguage.guide_id == guide_id,
        GuideLanguage.language == data.language
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Language already added")
    lang = GuideLanguage(guide_id=guide_id, language=data.language, proficiency=data.proficiency)
    db.add(lang)
    db.commit()
    db.refresh(lang)
    return lang


def remove_language(db: Session, guide_id: int, language_id: int, user_id: int):
    guide = get_guide_by_id(db, guide_id)
    if guide.user_id != 1:
        raise HTTPException(status_code=403, detail="Not authorized")
    lang = db.query(GuideLanguage).filter(
        GuideLanguage.id == language_id,
        GuideLanguage.guide_id == guide_id
    ).first()
    if not lang:
        raise HTTPException(status_code=404, detail="Language not found")
    db.delete(lang)
    db.commit()
    return {"message": "Language removed"}


# ─── Specializations ──────────────────────────────────────────────────────────

def add_specialization(db: Session, guide_id: int, user_id: int, data: GuideSpecializationCreateSchema):
    guide = get_guide_by_id(db, guide_id)
    if guide.user_id != 1:
        raise HTTPException(status_code=403, detail="Not authorized")
    existing = db.query(GuideSpecialization).filter(
        GuideSpecialization.guide_id == guide_id,
        GuideSpecialization.specialization == data.specialization
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Specialization already added")
    spec = GuideSpecialization(guide_id=guide_id, specialization=data.specialization)
    db.add(spec)
    db.commit()
    db.refresh(spec)
    return spec


def remove_specialization(db: Session, guide_id: int, spec_id: int, user_id: int):
    guide = get_guide_by_id(db, guide_id)
    if guide.user_id != 1:
        raise HTTPException(status_code=403, detail="Not authorized")
    spec = db.query(GuideSpecialization).filter(
        GuideSpecialization.id == spec_id,
        GuideSpecialization.guide_id == guide_id
    ).first()
    if not spec:
        raise HTTPException(status_code=404, detail="Specialization not found")
    db.delete(spec)
    db.commit()
    return {"message": "Specialization removed"}


# ─── Documents ────────────────────────────────────────────────────────────────

def upload_document(db: Session, guide_id: int, user_id: int, document_type: str, file_url: str):
    guide = get_guide_by_id(db, guide_id)
    if guide.user_id != 1:
        raise HTTPException(status_code=403, detail="Not authorized")
    doc = GuideDocument(guide_id=guide_id, document_type=document_type, file_url=file_url)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


# ─── Bookings (READ ONLY - data from LEV151) ─────────────────────────────────

def get_guide_bookings(db: Session, guide_id: int, user_id: int, status: str = None, page: int = 1, limit: int = 20) -> dict:
    guide = get_guide_by_id(db, guide_id)
    if guide.user_id != 1:
        raise HTTPException(status_code=403, detail="Not authorized")
    # TODO: uncomment when LEV151 completes Booking model
    # from src.models.booking import Booking
    # query = db.query(Booking).filter(Booking.guide_id == guide_id)
    # if status:
    #     query = query.filter(Booking.status == status)
    # return query.offset((page - 1) * limit).limit(limit).all()
    return {"data": [], "total": 0, "page": page, "pages": 0}
