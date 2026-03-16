from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile
from typing import Optional

from src.models.partner import Partner, PartnerDocument, PartnerPayout, PartnerStatus
from src.schemas.partner import (
    PartnerRegisterSchema, PartnerUpdateSchema,
    BankDetailsSchema, AvailabilityUpdateSchema, SettingsUpdateSchema
)


# ─── Helper ───────────────────────────────────────────────────────────────────

async def get_partner_by_user_id(db: Session, user_id: int) -> Partner:
    partner = db.query(Partner).filter(
        Partner.user_id == user_id,
        Partner.deleted_at == None
    ).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner profile not found")
    return partner


# ─── Register ─────────────────────────────────────────────────────────────────

async def register_partner(db: Session, data: PartnerRegisterSchema) -> Partner:
    existing = db.query(Partner).filter(Partner.user_id == 1).first()
    if existing:
        raise HTTPException(status_code=409, detail="Partner profile already exists")

    partner = Partner(
        user_id=1,  # temp until LEV148 auth is ready
        partner_type=data.partner_type,
        business_name=data.business_name,
        gstin=data.gstin,
        pan=data.pan,
        verification_status=PartnerStatus.APPLIED
    )
    db.add(partner)
    db.commit()
    db.refresh(partner)
    return partner


# ─── Profile ──────────────────────────────────────────────────────────────────

async def get_partner_profile(db: Session, user_id: int) -> Partner:
    return await get_partner_by_user_id(db, user_id)


async def update_partner_profile(db: Session, user_id: int, data: PartnerUpdateSchema) -> Partner:
    partner = await get_partner_by_user_id(db, user_id)
    update_data = data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(partner, field, value)
    db.commit()
    db.refresh(partner)
    return partner


# ─── Dashboard ────────────────────────────────────────────────────────────────

async def get_dashboard_stats(db: Session, user_id: int) -> dict:
    partner = await get_partner_by_user_id(db, user_id)
    return {
        "partner_id": partner.id,
        "business_name": partner.business_name,
        "verification_status": partner.verification_status,
        "total_earnings": partner.total_earnings,
        "wallet_balance": partner.wallet_balance,
        "todays_bookings": 0,       # temp until LEV151 ready
        "this_month_earnings": 0,   # temp until LEV151 ready
        "pending_payouts": 0        # temp until LEV151 ready
    }


# ─── Bookings (READ ONLY - data from LEV151) ──────────────────────────────────

async def get_partner_bookings(db: Session, user_id: int, status: str = None, page: int = 1, limit: int = 20) -> dict:
    # TODO: uncomment when LEV151 completes Booking model
    return {"data": [], "total": 0, "page": page, "pages": 0}


async def get_partner_booking_detail(db: Session, user_id: int, booking_id: int) -> dict:
    # TODO: uncomment when LEV151 completes Booking model
    return {"message": "Available after LEV151 completes booking module"}


async def accept_booking(db: Session, user_id: int, booking_id: int) -> dict:
    # TODO: uncomment when LEV151 completes Booking model
    return {"message": "Available after LEV151 completes booking module"}


async def reject_booking(db: Session, user_id: int, booking_id: int) -> dict:
    # TODO: uncomment when LEV151 completes Booking model
    return {"message": "Available after LEV151 completes booking module"}


# ─── Earnings ─────────────────────────────────────────────────────────────────

async def get_partner_earnings(db: Session, user_id: int) -> dict:
    partner = await get_partner_by_user_id(db, user_id)
    return {
        "total_earnings": partner.total_earnings,
        "wallet_balance": partner.wallet_balance,
        "this_month": 0,    # temp until LEV151 ready
        "last_month": 0     # temp until LEV151 ready
    }


async def get_earnings_report(db: Session, user_id: int) -> dict:
    await get_partner_by_user_id(db, user_id)
    return {"message": "Report available after LEV151 completes booking module"}


# ─── Payouts ──────────────────────────────────────────────────────────────────

async def get_partner_payouts(db: Session, user_id: int, page: int = 1, limit: int = 20):
    partner = await get_partner_by_user_id(db, user_id)
    payouts = db.query(PartnerPayout).filter(
        PartnerPayout.partner_id == partner.id
    ).order_by(PartnerPayout.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    return payouts


async def get_payout_detail(db: Session, payout_id: int):
    payout = db.query(PartnerPayout).filter(
        PartnerPayout.id == payout_id
    ).first()
    if not payout:
        raise HTTPException(status_code=404, detail="Payout not found")
    return payout


# ─── Bank Details ─────────────────────────────────────────────────────────────

async def update_bank_details(db: Session, user_id: int, data: BankDetailsSchema) -> Partner:
    partner = await get_partner_by_user_id(db, user_id)
    partner.bank_account_number = data.account_number
    partner.bank_ifsc = data.ifsc
    partner.bank_account_holder = data.holder_name
    db.commit()
    db.refresh(partner)
    return partner


# ─── Documents ────────────────────────────────────────────────────────────────

async def get_documents(db: Session, user_id: int):
    partner = await get_partner_by_user_id(db, user_id)
    return db.query(PartnerDocument).filter(
        PartnerDocument.partner_id == partner.id
    ).all()


async def upload_document(db: Session, user_id: int, document_type: str, file_url: str):
    partner = await get_partner_by_user_id(db, user_id)
    doc = PartnerDocument(
        partner_id=partner.id,
        document_type=document_type,
        file_url=file_url
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


async def delete_document(db: Session, user_id: int, doc_id: int):
    partner = await get_partner_by_user_id(db, user_id)
    doc = db.query(PartnerDocument).filter(
        PartnerDocument.id == doc_id,
        PartnerDocument.partner_id == partner.id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    db.delete(doc)
    db.commit()
    return {"message": "Document deleted"}


# ─── Availability ─────────────────────────────────────────────────────────────

async def update_availability(db: Session, user_id: int, data: AvailabilityUpdateSchema) -> Partner:
    partner = await get_partner_by_user_id(db, user_id)
    partner.unavailable_dates = data.unavailable_dates
    db.commit()
    db.refresh(partner)
    return partner


# ─── Settings ─────────────────────────────────────────────────────────────────

async def update_settings(db: Session, user_id: int, data: SettingsUpdateSchema) -> Partner:
    partner = await get_partner_by_user_id(db, user_id)
    if data.auto_accept_bookings is not None:
        partner.auto_accept_bookings = data.auto_accept_bookings
    if data.notification_preferences is not None:
        partner.notification_preferences = data.notification_preferences
    db.commit()
    db.refresh(partner)
    return partner


# ─── Analytics ────────────────────────────────────────────────────────────────

async def get_analytics(db: Session, user_id: int) -> dict:
    partner = await get_partner_by_user_id(db, user_id)
    return {
        "partner_id": partner.id,
        "total_earnings": partner.total_earnings,
        "total_bookings": 0,        # temp until LEV151 ready
        "avg_rating": 0.0,          # temp until Review module ready
        "this_month_bookings": 0    # temp until LEV151 ready
    }


# ─── Notifications ────────────────────────────────────────────────────────────

async def get_partner_notifications(db: Session, user_id: int, page: int = 1, limit: int = 20) -> dict:
    # TODO: uncomment when Notification module is ready
    return {"data": [], "total": 0, "page": page, "pages": 0}


# ─── Reviews ──────────────────────────────────────────────────────────────────

async def get_partner_reviews(db: Session, user_id: int, page: int = 1, limit: int = 20) -> dict:
    # TODO: uncomment when Review module is ready
    return {"data": [], "total": 0, "page": page, "pages": 0}


async def reply_to_review(db: Session, user_id: int, review_id: int, data) -> dict:
    # TODO: uncomment when Review module is ready
    return {"message": "Available after Review module is ready"}
