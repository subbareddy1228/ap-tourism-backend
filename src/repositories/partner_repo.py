# # ✅ Correct version of partner_repo.py
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import select
# from fastapi import HTTPException
# from src.models.partner import Partner, PartnerDocument, PartnerPayout
# from uuid import UUID

# # async def get_partner_by_id(db: AsyncSession, partner_id: UUID) -> Partner:
# #     result = await db.execute(
# #         select(Partner).where(Partner.id == partner_id, Partner.deleted_at == None)
# #     )
# #     partner = result.scalar_one_or_none()
# #     if not partner:
# #         raise HTTPException(status_code=404, detail="Partner not found")
# #     return partner
# async def get_partner_by_id(db: AsyncSession, partner_id: UUID) -> Partner:
#     result = await db.execute(
#         select(Partner).where(Partner.id == partner_id)
#     )
#     partner = result.scalar_one_or_none()
#     if not partner:
#         raise HTTPException(status_code=404, detail="Partner not found")
#     return partner

# async def get_partner_by_user_id(db: AsyncSession, user_id: UUID) -> Partner:
#     result = await db.execute(
#         select(Partner).where(Partner.user_id == user_id)
#     )
#     return result.scalar_one_or_none()

# async def get_partner_by_user_id(db: AsyncSession, user_id: UUID) -> Partner:
#     result = await db.execute(
#         select(Partner).where(Partner.user_id == user_id, Partner.deleted_at == None)
#     )
#     return result.scalar_one_or_none()

# async def create_partner(db: AsyncSession, partner: Partner) -> Partner:
#     db.add(partner)
#     await db.commit()
#     await db.refresh(partner)
#     return partner

# async def update_partner(db: AsyncSession, partner: Partner) -> Partner:
#     await db.commit()
#     await db.refresh(partner)
#     return partner

# async def get_all_documents(db: AsyncSession, partner_id: UUID):
#     result = await db.execute(
#         select(PartnerDocument).where(PartnerDocument.partner_id == partner_id)
#     )
#     return result.scalars().all()

# async def get_document_by_id(db: AsyncSession, doc_id: UUID, partner_id: UUID):
#     result = await db.execute(
#         select(PartnerDocument).where(
#             PartnerDocument.id == doc_id,
#             PartnerDocument.partner_id == partner_id
#         )
#     )
#     return result.scalar_one_or_none()

# async def create_document(db: AsyncSession, doc: PartnerDocument) -> PartnerDocument:
#     db.add(doc)
#     await db.commit()
#     await db.refresh(doc)
#     return doc

# async def delete_document(db: AsyncSession, doc: PartnerDocument):
#     await db.delete(doc)
#     await db.commit()

# async def get_all_payouts(db: AsyncSession, partner_id: UUID, page: int, limit: int):
#     result = await db.execute(
#         select(PartnerPayout)
#         .where(PartnerPayout.partner_id == partner_id)
#         .order_by(PartnerPayout.created_at.desc())
#         .offset((page - 1) * limit)
#         .limit(limit)
#     )
#     return result.scalars().all()

# async def get_payout_by_id(db: AsyncSession, payout_id: UUID):
#     result = await db.execute(
#         select(PartnerPayout).where(PartnerPayout.id == payout_id)
#     )
#     return result.scalar_one_or_none()
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from src.models.partner import Partner, PartnerDocument, PartnerPayout
from uuid import UUID


async def get_partner_by_id(db: AsyncSession, partner_id: UUID) -> Partner:
    result = await db.execute(
        select(Partner).where(Partner.id == partner_id)
    )
    partner = result.scalar_one_or_none()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    return partner


async def get_partner_by_user_id(db: AsyncSession, user_id: UUID) -> Partner:
    result = await db.execute(
        select(Partner).where(Partner.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def create_partner(db: AsyncSession, partner: Partner) -> Partner:
    db.add(partner)
    await db.commit()
    await db.refresh(partner)
    return partner


async def update_partner(db: AsyncSession, partner: Partner) -> Partner:
    await db.commit()
    await db.refresh(partner)
    return partner


async def get_all_documents(db: AsyncSession, partner_id: UUID):
    result = await db.execute(
        select(PartnerDocument).where(PartnerDocument.partner_id == partner_id)
    )
    return result.scalars().all()


async def get_document_by_id(db: AsyncSession, doc_id: UUID, partner_id: UUID):
    result = await db.execute(
        select(PartnerDocument).where(
            PartnerDocument.id == doc_id,
            PartnerDocument.partner_id == partner_id
        )
    )
    return result.scalar_one_or_none()


async def create_document(db: AsyncSession, doc: PartnerDocument) -> PartnerDocument:
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


async def delete_document(db: AsyncSession, doc: PartnerDocument):
    await db.delete(doc)
    await db.commit()


async def get_all_payouts(db: AsyncSession, partner_id: UUID, page: int, limit: int):
    result = await db.execute(
        select(PartnerPayout)
        .where(PartnerPayout.partner_id == partner_id)
        .order_by(PartnerPayout.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    return result.scalars().all()


async def get_payout_by_id(db: AsyncSession, payout_id: UUID):
    result = await db.execute(
        select(PartnerPayout).where(PartnerPayout.id == payout_id)
    )
    return result.scalar_one_or_none()