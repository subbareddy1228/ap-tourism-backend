from sqlalchemy.orm import Session
from fastapi import HTTPException
from src.models.guide import Guide, GuideLanguage, GuideSpecialization, GuideDocument, GuideStatus


async def get_guide_by_id(db: Session, guide_id: int) -> Guide:
    return db.query(Guide).filter(
        Guide.id == guide_id,
        Guide.deleted_at == None
    ).first()


async def get_guide_by_user_id(db: Session, user_id: int) -> Guide:
    return db.query(Guide).filter(
        Guide.user_id == user_id,
        Guide.deleted_at == None
    ).first()


async def create_guide(db: Session, guide: Guide) -> Guide:
    db.add(guide)
    db.commit()
    db.refresh(guide)
    return guide


async def update_guide(db: Session, guide: Guide) -> Guide:
    db.commit()
    db.refresh(guide)
    return guide


async def get_active_guides(db: Session, page: int, limit: int):
    return db.query(Guide).filter(
        Guide.status == GuideStatus.ACTIVE,
        Guide.deleted_at == None
    ).offset((page - 1) * limit).limit(limit).all()


async def get_featured_guides(db: Session):
    return db.query(Guide).filter(
        Guide.is_featured == True,
        Guide.status == GuideStatus.ACTIVE,
        Guide.deleted_at == None
    ).order_by(Guide.rating.desc()).limit(10).all()


async def add_language(db: Session, lang: GuideLanguage) -> GuideLanguage:
    db.add(lang)
    db.commit()
    db.refresh(lang)
    return lang


async def delete_language(db: Session, lang: GuideLanguage):
    db.delete(lang)
    db.commit()


async def add_specialization(db: Session, spec: GuideSpecialization) -> GuideSpecialization:
    db.add(spec)
    db.commit()
    db.refresh(spec)
    return spec


async def delete_specialization(db: Session, spec: GuideSpecialization):
    db.delete(spec)
    db.commit()


async def add_document(db: Session, doc: GuideDocument) -> GuideDocument:
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc
