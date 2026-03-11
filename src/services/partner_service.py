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


def get_dashboard_stats(db: Session, user_id: int) -> dict:
    partner = get_partner_profile(db, user_id)
    today = date.today()

    # Import here to avoid circular imports
    from src.models.booking import Booking
    todays_bookings = db.query(Booking).filter(
        Booking.partner_id == partner.id,
        Booking.travel_date == today
    ).count()

    # This month earnings
    from sqlalchemy import extract
    from src.models.booking import Booking
    this_month_earnings = db.query(Booking).filter(
        Booking.partner_id == partner.id,
        Booking.status == "COMPLETED",
        extract("month", Booking.created_at) == today.month,
        extract("year", Booking.created_at) == today.year
    ).with_entities(db.func.sum(Booking.amount)).scalar() or 0.0

    pending_payouts = db.query(PartnerPayout).filter(
        PartnerPayout.partner_id == partner.id,
        PartnerPayout.status == "PENDING"
    ).with_entities(db.func.sum(PartnerPayout.amount)).scalar() or 0.0

    return {
        "todays_bookings": todays_bookings,
        "this_month_earnings": this_month_earnings,
        "pending_payouts": pending_payouts,
        "active_listings": 0,  # Count from hotel/vehicle/guide tables based on partner type
    }


# ─── Bookings ─────────────────────────────────────────────────────────────────

def get_partner_bookings(db: Session, user_id: int, status: Optional[str], page: int, limit: int) -> list:
    partner = get_partner_profile(db, user_id)
    from src.models.booking import Booking
    query = db.query(Booking).filter(Booking.partner_id == partner.id)
    if status:
        query = query.filter(Booking.status == status)
    return query.offset((page - 1) * limit).limit(limit).all()


def get_partner_booking_detail(db: Session, user_id: int, booking_id: int):
    partner = get_partner_profile(db, user_id)
    from src.models.booking import Booking
    booking = db.query(Booking).filter(
        Booking.id == booking_id,
        Booking.partner_id == partner.id
    ).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


def accept_booking(db: Session, user_id: int, booking_id: int):
    booking = get_partner_booking_detail(db, user_id, booking_id)
    if booking.status != "PENDING":
        raise HTTPException(status_code=400, detail="Only PENDING bookings can be accepted")
    booking.status = "CONFIRMED"
    db.commit()
    db.refresh(booking)
    # TODO: trigger notification to traveler
    return booking


def reject_booking(db: Session, user_id: int, booking_id: int, data: BookingRejectSchema):
    booking = get_partner_booking_detail(db, user_id, booking_id)
    if booking.status != "PENDING":
        raise HTTPException(status_code=400, detail="Only PENDING bookings can be rejected")
    booking.status = "REJECTED"
    booking.rejection_reason = data.reason
    db.commit()
    db.refresh(booking)
    # TODO: trigger admin reassignment + notify traveler
    return booking


# ─── Earnings ─────────────────────────────────────────────────────────────────

def get_earnings_summary(db: Session, user_id: int) -> dict:
    partner = get_partner_profile(db, user_id)
    today = date.today()
    from sqlalchemy import extract
    from src.models.booking import Booking

    this_month = db.query(Booking).filter(
        Booking.partner_id == partner.id,
        Booking.status == "COMPLETED",
        extract("month", Booking.created_at) == today.month,
        extract("year", Booking.created_at) == today.year
    ).with_entities(db.func.sum(Booking.amount)).scalar() or 0.0

    pending_payout = db.query(PartnerPayout).filter(
        PartnerPayout.partner_id == partner.id,
        PartnerPayout.status == "PENDING"
    ).with_entities(db.func.sum(PartnerPayout.amount)).scalar() or 0.0

    return {
        "total_earned": partner.total_earnings,
        "this_month": this_month,
        "pending_payout": pending_payout,
        "commission_rate": partner.commission_rate,
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

def get_partner_notifications(db: Session, user_id: int, page: int, limit: int) -> list:
    partner = get_partner_profile(db, user_id)
    from src.models.notification import Notification
    return db.query(Notification).filter(
        Notification.user_id == partner.user_id
    ).order_by(Notification.created_at.desc()).offset((page - 1) * limit).limit(limit).all()


# ─── Reviews ──────────────────────────────────────────────────────────────────

def get_partner_reviews(db: Session, user_id: int, page: int, limit: int) -> list:
    partner = get_partner_profile(db, user_id)
    from src.models.review import Review
    return db.query(Review).filter(
        Review.entity_id == partner.id,
        Review.entity_type == partner.partner_type.value
    ).order_by(Review.created_at.desc()).offset((page - 1) * limit).limit(limit).all()


def reply_to_review(db: Session, user_id: int, review_id: int, data: ReviewReplySchema):
    partner = get_partner_profile(db, user_id)
    from src.models.review import Review
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    review.partner_reply = data.reply
    review.replied_at = datetime.utcnow()
    db.commit()
    db.refresh(review)
    return review