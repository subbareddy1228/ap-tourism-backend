from sqlalchemy.orm import Session
from fastapi import HTTPException
from src.models.partner import Partner, PartnerDocument, PartnerPayout


async def get_partner_by_id(db: Session, partner_id: int) -> Partner:
    partner = db.query(Partner).filter(
        Partner.id == partner_id,
        Partner.deleted_at == None
    ).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    return partner


async def get_partner_by_user_id(db: Session, user_id: int) -> Partner:
    return db.query(Partner).filter(
        Partner.user_id == user_id,
        Partner.deleted_at == None
    ).first()


async def create_partner(db: Session, partner: Partner) -> Partner:
    db.add(partner)
    db.commit()
    db.refresh(partner)
    return partner


async def update_partner(db: Session, partner: Partner) -> Partner:
    db.commit()
    db.refresh(partner)
    return partner


async def get_all_documents(db: Session, partner_id: int):
    return db.query(PartnerDocument).filter(
        PartnerDocument.partner_id == partner_id
    ).all()


async def get_document_by_id(db: Session, doc_id: int, partner_id: int):
    return db.query(PartnerDocument).filter(
        PartnerDocument.id == doc_id,
        PartnerDocument.partner_id == partner_id
    ).first()


async def create_document(db: Session, doc: PartnerDocument) -> PartnerDocument:
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


async def delete_document(db: Session, doc: PartnerDocument):
    db.delete(doc)
    db.commit()


async def get_all_payouts(db: Session, partner_id: int, page: int, limit: int):
    return db.query(PartnerPayout).filter(
        PartnerPayout.partner_id == partner_id
    ).order_by(PartnerPayout.created_at.desc()).offset((page - 1) * limit).limit(limit).all()


async def get_payout_by_id(db: Session, payout_id: int):
    return db.query(PartnerPayout).filter(
        PartnerPayout.id == payout_id
    ).first()
