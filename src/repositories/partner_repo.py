from sqlalchemy.orm import Session
from sqlalchemy import extract, func
from typing import Optional, List
from datetime import date

from src.models.partner import Partner, PartnerDocument, PartnerPayout, PartnerStatus


# ─── Partner CRUD ─────────────────────────────────────────────────────────────

def create_partner(db: Session, user_id: int, partner_type: str, business_name: str, gstin: str = None, pan: str = None) -> Partner:
    partner = Partner(
        user_id=user_id,
        partner_type=partner_type,
        business_name=business_name,
        gstin=gstin,
        pan=pan,
        verification_status=PartnerStatus.APPLIED
    )
    db.add(partner)
    db.commit()
    db.refresh(partner)
    return partner


def get_partner_by_user_id(db: Session, user_id: int) -> Optional[Partner]:
    return db.query(Partner).filter(
        Partner.user_id == user_id,
        Partner.deleted_at == None
    ).first()


def get_partner_by_id(db: Session, partner_id: int) -> Optional[Partner]:
    return db.query(Partner).filter(
        Partner.id == partner_id,
        Partner.deleted_at == None
    ).first()


def update_partner(db: Session, partner: Partner, data: dict) -> Partner:
    for field, value in data.items():
        setattr(partner, field, value)
    db.commit()
    db.refresh(partner)
    return partner


# ─── Bank Details ─────────────────────────────────────────────────────────────

def update_bank_details(db: Session, partner: Partner, account_number: str, ifsc: str, holder_name: str) -> Partner:
    partner.bank_account_number = account_number
    partner.bank_ifsc = ifsc
    partner.bank_account_holder = holder_name
    db.commit()
    db.refresh(partner)
    return partner


# ─── Availability ─────────────────────────────────────────────────────────────

def update_availability(db: Session, partner: Partner, unavailable_dates: list) -> Partner:
    partner.unavailable_dates = unavailable_dates
    db.commit()
    db.refresh(partner)
    return partner


# ─── Settings ─────────────────────────────────────────────────────────────────

def update_settings(db: Session, partner: Partner, auto_accept: bool = None, notification_prefs: dict = None) -> Partner:
    if auto_accept is not None:
        partner.auto_accept_bookings = auto_accept
    if notification_prefs is not None:
        partner.notification_preferences = notification_prefs
    db.commit()
    db.refresh(partner)
    return partner


# ─── Documents ────────────────────────────────────────────────────────────────

def get_documents(db: Session, partner_id: int) -> List[PartnerDocument]:
    return db.query(PartnerDocument).filter(
        PartnerDocument.partner_id == partner_id
    ).all()


def create_document(db: Session, partner_id: int, document_type: str, file_url: str) -> PartnerDocument:
    doc = PartnerDocument(
        partner_id=partner_id,
        document_type=document_type,
        file_url=file_url
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def get_document_by_id(db: Session, doc_id: int, partner_id: int) -> Optional[PartnerDocument]:
    return db.query(PartnerDocument).filter(
        PartnerDocument.id == doc_id,
        PartnerDocument.partner_id == partner_id
    ).first()


def delete_document(db: Session, doc: PartnerDocument):
    db.delete(doc)
    db.commit()


# ─── Payouts ──────────────────────────────────────────────────────────────────

def get_payouts(db: Session, partner_id: int, page: int, limit: int) -> List[PartnerPayout]:
    return db.query(PartnerPayout).filter(
        PartnerPayout.partner_id == partner_id
    ).order_by(PartnerPayout.created_at.desc()).offset((page - 1) * limit).limit(limit).all()


def get_payout_by_id(db: Session, payout_id: int, partner_id: int) -> Optional[PartnerPayout]:
    return db.query(PartnerPayout).filter(
        PartnerPayout.id == payout_id,
        PartnerPayout.partner_id == partner_id
    ).first()


def get_pending_payout_total(db: Session, partner_id: int) -> float:
    result = db.query(func.sum(PartnerPayout.amount)).filter(
        PartnerPayout.partner_id == partner_id,
        PartnerPayout.status == "PENDING"
    ).scalar()
    return result or 0.0


# ─── Earnings ─────────────────────────────────────────────────────────────────

def get_this_month_earnings(db: Session, partner_id: int) -> float:
    today = date.today()
    try:
        from src.models.booking import Booking
        result = db.query(func.sum(Booking.amount)).filter(
            Booking.partner_id == partner_id,
            Booking.status == "COMPLETED",
            extract("month", Booking.created_at) == today.month,
            extract("year", Booking.created_at) == today.year
        ).scalar()
        return result or 0.0
    except Exception:
        return 0.0


def get_todays_booking_count(db: Session, partner_id: int) -> int:
    today = date.today()
    try:
        from src.models.booking import Booking
        return db.query(Booking).filter(
            Booking.partner_id == partner_id,
            Booking.travel_date == today
        ).count()
    except Exception:
        return 0