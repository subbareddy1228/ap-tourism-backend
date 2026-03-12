from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile
from datetime import datetime, date
from typing import List, Optional

from src.models.partner import Partner, PartnerDocument, PartnerPayout, PartnerStatus
from src.schemas.partner import (
    PartnerRegisterSchema, PartnerUpdateSchema, BankDetailsSchema,
    AvailabilityUpdateSchema, PartnerSettingsSchema, ReviewReplySchema,
    BookingRejectSchema
)


# ─── Registration ─────────────────────────────────────────────────────────────

def register_partner(db: Session, data: PartnerRegisterSchema) -> Partner:
    existing = db.query(Partner).first()
    if existing:
        raise HTTPException(status_code=409, detail="Partner profile already exists for this user")

    partner = Partner(
        #user_id=user_id,
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

def get_partner_profile(db: Session, user_id: int) -> Partner:
    partner = db.query(Partner).filter(
        Partner.user_id == user_id,
        Partner.deleted_at == None
    ).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner profile not found")
    return partner


def update_partner_profile(db: Session, user_id: int, data: PartnerUpdateSchema) -> Partner:
    partner = get_partner_profile(db, user_id)
    update_data = data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(partner, field, value)
    db.commit()
    db.refresh(partner)
    return partner

def get_partner_by_user_id(db: Session, user_id: int):
    partner = db.query(Partner).filter(
        Partner.user_id == user_id,
        Partner.deleted_at == None
    ).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    return partner

def get_dashboard_stats(db: Session, user_id: int) -> dict:
    partner = get_partner_by_user_id(db, user_id=1)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")

    return {
        "partner_id": partner.id,
        "total_earnings": partner.total_earnings,
        "wallet_balance": partner.wallet_balance,
        "todays_bookings": 0,       # temp until LEV151 ready
        "this_month_earnings": 0,   # temp until LEV151 ready
        "pending_payouts": 0
    }


# ─── Bookings ─────────────────────────────────────────────────────────────────

def get_partner_bookings(db: Session, user_id: int, status: str = None, page: int = 1, limit: int = 20):
    partner = get_partner_by_user_id(db, user_id)
    # Booking model not ready yet (LEV151)
    return {
        "data": [],
        "total": 0,
        "page": page,
        "pages": 0,
        "message": "Bookings will be available when LEV151 completes booking module"
    }


def get_partner_booking_detail(db: Session, user_id: int, booking_id: int):
    # Booking model not ready yet (LEV151 pending)
    return {"message": "Booking detail will be available when LEV151 completes booking module"}


def accept_booking(db: Session, user_id: int, booking_id: int) -> dict:
    # TODO: uncomment when LEV151 completes Booking model
    return {"message": "Available after LEV151 completes booking module"}


def reject_booking(db: Session, user_id: int, booking_id: int) -> dict:
    # TODO: uncomment when LEV151 completes Booking model
    return {"message": "Available after LEV151 completes booking module"}


# ─── Earnings ─────────────────────────────────────────────────────────────────

def get_earnings_summary(db: Session, user_id: int):
    # from src.models.booking import Booking  # comment this line
    partner = get_partner_by_user_id(db, user_id)
    return {
        "total_earnings": partner.total_earnings,
        "wallet_balance": partner.wallet_balance,
        "this_month": 0,
        "last_month": 0
    }


# ─── Payouts ──────────────────────────────────────────────────────────────────

def get_payouts(db: Session, user_id: int, page: int, limit: int) -> list:
    partner = get_partner_profile(db, user_id)
    return db.query(PartnerPayout).filter(
        PartnerPayout.partner_id == partner.id
    ).offset((page - 1) * limit).limit(limit).all()


def get_payout_detail(db: Session, user_id: int, payout_id: int):
    partner = get_partner_profile(db, user_id)
    payout = db.query(PartnerPayout).filter(
        PartnerPayout.id == payout_id,
        PartnerPayout.partner_id == partner.id
    ).first()
    if not payout:
        raise HTTPException(status_code=404, detail="Payout not found")
    return payout


# ─── Bank Details ─────────────────────────────────────────────────────────────

def update_bank_details(db: Session, user_id: int, data: BankDetailsSchema) -> Partner:
    partner = get_partner_profile(db, user_id)
    partner.bank_account_number = data.account_number
    partner.bank_ifsc = data.ifsc
    partner.bank_account_holder = data.account_holder_name
    db.commit()
    db.refresh(partner)
    return partner


# ─── Documents ────────────────────────────────────────────────────────────────

def get_documents(db: Session, user_id: int) -> list:
    partner = get_partner_profile(db, user_id)
    return db.query(PartnerDocument).filter(
        PartnerDocument.partner_id == partner.id
    ).all()


def upload_document(db: Session, user_id: int, document_type: str, file_url: str):
    partner = get_partner_profile(db, user_id)
    doc = PartnerDocument(
        partner_id=partner.id,
        document_type=document_type,
        file_url=file_url
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def delete_document(db: Session, user_id: int, doc_id: int):
    partner = get_partner_profile(db, user_id)
    doc = db.query(PartnerDocument).filter(
        PartnerDocument.id == doc_id,
        PartnerDocument.partner_id == partner.id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.is_verified:
        raise HTTPException(status_code=400, detail="Cannot delete a verified document")
    db.delete(doc)
    db.commit()
    return {"message": "Document deleted"}


# ─── Settings ─────────────────────────────────────────────────────────────────

def update_availability(db: Session, user_id: int, data: AvailabilityUpdateSchema) -> Partner:
    partner = get_partner_profile(db, user_id)
    partner.unavailable_dates = data.unavailable_dates
    db.commit()
    db.refresh(partner)
    return partner


def update_settings(db: Session, user_id: int, data: PartnerSettingsSchema) -> Partner:
    partner = get_partner_profile(db, user_id)
    if data.auto_accept_bookings is not None:
        partner.auto_accept_bookings = data.auto_accept_bookings
    if data.notification_preferences is not None:
        partner.notification_preferences = data.notification_preferences
    db.commit()
    db.refresh(partner)
    return partner


# ─── Analytics ────────────────────────────────────────────────────────────────

def get_analytics(db: Session, user_id: int) -> dict:
    partner = get_partner_profile(db, user_id)
    # TODO: build full analytics — booking trends, revenue chart, occupancy rate
    return {
        "partner_id": partner.id,
        "booking_trends": [],
        "revenue_chart": [],
        "occupancy_rate": 0.0
    }


# ─── Notifications ────────────────────────────────────────────────────────────

def get_partner_notifications(db: Session, user_id: int, page: int = 1, limit: int = 20) -> dict:
    # TODO: uncomment when Notification module is ready
    # from src.models.notification import Notification
    return {"data": [], "total": 0, "page": page, "pages": 0}


# ─── Reviews ──────────────────────────────────────────────────────────────────

def get_partner_reviews(db: Session, user_id: int, page: int = 1, limit: int = 20) -> list:
    partner = get_partner_profile(db, user_id)
    from src.models.review import Review
    return db.query(Review).filter(
        Review.entity_id == partner.id,
        Review.entity_type == partner.partner_type.value
    ).order_by(Review.created_at.desc()).offset((page - 1) * limit).limit(limit).all()


def reply_to_review(db: Session, user_id: int, review_id: int, data) -> dict:
    # TODO: uncomment when Review module is ready
    # from src.models.review import Review
    return {"message": "Available after Review module is ready"}