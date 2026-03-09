from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List

from src.models.guide import Guide, GuideLanguage, GuideSpecialization, GuideDocument, GuideStatus


# ─── Guide CRUD ───────────────────────────────────────────────────────────────

def create_guide(db: Session, partner_id: int, user_id: int, data: dict) -> Guide:
    guide = Guide(partner_id=partner_id, user_id=user_id, **data)
    db.add(guide)
    db.commit()
    db.refresh(guide)
    return guide


def get_guide_by_id(db: Session, guide_id: int) -> Optional[Guide]:
    return db.query(Guide).filter(
        Guide.id == guide_id,
        Guide.deleted_at == None
    ).first()


def get_guide_by_partner_id(db: Session, partner_id: int) -> Optional[Guide]:
    return db.query(Guide).filter(
        Guide.partner_id == partner_id,
        Guide.deleted_at == None
    ).first()


def get_guide_by_user_id(db: Session, user_id: int) -> Optional[Guide]:
    return db.query(Guide).filter(
        Guide.user_id == user_id,
        Guide.deleted_at == None
    ).first()


def update_guide(db: Session, guide: Guide, data: dict) -> Guide:
    for field, value in data.items():
        setattr(guide, field, value)
    db.commit()
    db.refresh(guide)
    return guide


# ─── Listing / Filters ────────────────────────────────────────────────────────

def get_all_guides(db: Session, city: str = None, language: str = None, specialization: str = None, min_rating: float = None, page: int = 1, limit: int = 20) -> dict:
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


def get_featured_guides(db: Session, limit: int = 10) -> List[Guide]:
    return db.query(Guide).filter(
        Guide.is_featured == True,
        Guide.status == GuideStatus.ACTIVE,
        Guide.deleted_at == None
    ).order_by(Guide.rating.desc()).limit(limit).all()


def get_guides_by_language(db: Session, language: str, page: int, limit: int) -> List[Guide]:
    return db.query(Guide).join(GuideLanguage).filter(
        GuideLanguage.language.ilike(f"%{language}%"),
        Guide.status == GuideStatus.ACTIVE,
        Guide.deleted_at == None
    ).offset((page - 1) * limit).limit(limit).all()


def get_guides_by_specialization(db: Session, specialization: str, page: int, limit: int) -> List[Guide]:
    return db.query(Guide).join(GuideSpecialization).filter(
        GuideSpecialization.specialization == specialization,
        Guide.status == GuideStatus.ACTIVE,
        Guide.deleted_at == None
    ).offset((page - 1) * limit).limit(limit).all()


def get_guides_by_city(db: Session, city: str, page: int, limit: int) -> List[Guide]:
    return db.query(Guide).filter(
        Guide.city.ilike(f"%{city}%"),
        Guide.status == GuideStatus.ACTIVE,
        Guide.deleted_at == None
    ).offset((page - 1) * limit).limit(limit).all()


# ─── Availability ─────────────────────────────────────────────────────────────

def update_availability(db: Session, guide: Guide, unavailable_dates: list) -> Guide:
    guide.unavailable_dates = unavailable_dates
    db.commit()
    db.refresh(guide)
    return guide


# ─── Languages ────────────────────────────────────────────────────────────────

def get_language_by_id(db: Session, language_id: int, guide_id: int) -> Optional[GuideLanguage]:
    return db.query(GuideLanguage).filter(
        GuideLanguage.id == language_id,
        GuideLanguage.guide_id == guide_id
    ).first()


def get_language_by_name(db: Session, guide_id: int, language: str) -> Optional[GuideLanguage]:
    return db.query(GuideLanguage).filter(
        GuideLanguage.guide_id == guide_id,
        GuideLanguage.language == language
    ).first()


def create_language(db: Session, guide_id: int, language: str, proficiency: str) -> GuideLanguage:
    lang = GuideLanguage(guide_id=guide_id, language=language, proficiency=proficiency)
    db.add(lang)
    db.commit()
    db.refresh(lang)
    return lang


def delete_language(db: Session, lang: GuideLanguage):
    db.delete(lang)
    db.commit()


# ─── Specializations ──────────────────────────────────────────────────────────

def get_specialization_by_id(db: Session, spec_id: int, guide_id: int) -> Optional[GuideSpecialization]:
    return db.query(GuideSpecialization).filter(
        GuideSpecialization.id == spec_id,
        GuideSpecialization.guide_id == guide_id
    ).first()


def get_specialization_by_type(db: Session, guide_id: int, specialization: str) -> Optional[GuideSpecialization]:
    return db.query(GuideSpecialization).filter(
        GuideSpecialization.guide_id == guide_id,
        GuideSpecialization.specialization == specialization
    ).first()


def create_specialization(db: Session, guide_id: int, specialization: str) -> GuideSpecialization:
    spec = GuideSpecialization(guide_id=guide_id, specialization=specialization)
    db.add(spec)
    db.commit()
    db.refresh(spec)
    return spec


def delete_specialization(db: Session, spec: GuideSpecialization):
    db.delete(spec)
    db.commit()


# ─── Documents ────────────────────────────────────────────────────────────────

def create_document(db: Session, guide_id: int, document_type: str, file_url: str) -> GuideDocument:
    doc = GuideDocument(guide_id=guide_id, document_type=document_type, file_url=file_url)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def get_documents(db: Session, guide_id: int) -> List[GuideDocument]:
    return db.query(GuideDocument).filter(GuideDocument.guide_id == guide_id).all()