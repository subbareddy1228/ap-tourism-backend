from select import select

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from src.models.guide import Guide, GuideLanguage, GuideSpecialization, GuideDocument, GuideStatus


async def get_guide_by_id(db: AsyncSession, guide_id: int) -> Guide:
    return await db.execute(
        select(Guide).where(
            Guide.id == guide_id,
            Guide.deleted_at == None
        )
    ).scalars().first()


async def get_guide_by_user_id(db: AsyncSession, user_id: int) -> Guide:
    return await db.execute(
        select(Guide).where(
            Guide.user_id == user_id,
            Guide.deleted_at == None
        )
    ).scalars().first()


async def create_guide(db: AsyncSession, guide: Guide) -> Guide:
    db.add(guide)
    await db.commit()
    db.refresh(guide)
    return guide


async def update_guide(db: AsyncSession, guide: Guide) -> Guide:
    await db.commit()
    db.refresh(guide)
    return guide


async def get_active_guides(db: AsyncSession, page: int, limit: int):
    return await db.execute(
        select(Guide).where(
            Guide.status == GuideStatus.ACTIVE,
            Guide.deleted_at == None
        ).offset((page - 1) * limit).limit(limit)
    ).scalars().all()


async def get_featured_guides(db: AsyncSession):
    return await db.execute(
        select(Guide).where(
            Guide.is_featured == True,
            Guide.status == GuideStatus.ACTIVE,
            Guide.deleted_at == None
        ).order_by(Guide.rating.desc()).limit(10)
    ).scalars().all()


async def add_language(db: AsyncSession, lang: GuideLanguage) -> GuideLanguage:
    db.add(lang)
    await db.commit()
    db.refresh(lang)
    return lang


async def delete_language(db: AsyncSession, lang: GuideLanguage):
    db.delete(lang)
    await db.commit()


async def add_specialization(db: AsyncSession, spec: GuideSpecialization) -> GuideSpecialization:
    db.add(spec)
    await db.commit()
    db.refresh(spec)
    return spec


async def delete_specialization(db: AsyncSession, spec: GuideSpecialization):
    db.delete(spec)
    await db.commit()


async def add_document(db: AsyncSession, doc: GuideDocument) -> GuideDocument:
    db.add(doc)
    await   db.commit()
    db.refresh(doc)
    return doc
