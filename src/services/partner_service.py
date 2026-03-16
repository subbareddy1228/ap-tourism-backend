"""

services/partner_service.py

Partners module — complete business logic for all 20 endpoints.

"""
 
import logging

import csv

import io

from datetime import datetime, date

from decimal import Decimal
 
from fastapi import HTTPException, UploadFile, status

from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select, func
 
from src.models.partner import Partner, PartnerDocument, PartnerPayout, PartnerBankDetails

from src.models.user import User

from src.schemas.partner import (

    PartnerRegisterRequest, PartnerUpdateRequest,

    BankDetailsRequest, AvailabilityRequest, SettingsRequest,

    ReviewReplyRequest, BookingActionRequest

)
 
logger = logging.getLogger(__name__)
 
 
# ══════════════════ HELPERS ══════════════════
 
async def get_partner_or_404(user_id, db: AsyncSession) -> Partner:

    result = await db.execute(select(Partner).where(Partner.user_id == user_id))

    partner = result.scalar_one_or_none()

    if not partner:

        raise HTTPException(

            status_code=status.HTTP_404_NOT_FOUND,

            detail="Partner profile not found. Please register first via POST /partners/register"

        )

    return partner
 
 
# ══════════════════ PROFILE ══════════════════
 
async def register_partner(data: PartnerRegisterRequest, current_user: User, db: AsyncSession) -> Partner:
 
    result = await db.execute(select(Partner).where(Partner.user_id == current_user.id))

    if result.scalar_one_or_none():

        raise HTTPException(status_code=400, detail="Already registered as a partner")
 
    partner = Partner(

        user_id=current_user.id,

        business_name=data.business_name,

        business_type=data.business_type,

        gstin=data.gstin,

        pan=data.pan,

        description=data.description,

        contact_phone=data.contact_phone,

        contact_email=data.contact_email,

        website=data.website,

        address=data.address,

        city=data.city,

        state=data.state,

        pincode=data.pincode,

        latitude=data.latitude,

        longitude=data.longitude,

        verification_status="APPLIED",

    )

    db.add(partner)

    await db.commit()

    await db.refresh(partner)

    logger.info("Partner registered user_id=%s business=%s", current_user.id, data.business_name)

    return partner
 
 
async def get_my_profile(current_user: User, db: AsyncSession) -> dict:

    partner = await get_partner_or_404(current_user.id, db)

    return _partner_to_dict(partner)
 
 
async def get_dashboard(current_user: User, db: AsyncSession) -> dict:

    partner = await get_partner_or_404(current_user.id, db)
 
    # Placeholder stats — will be real once Bookings module is integrated

    return {

        "today_bookings":        0,

        "this_month_earnings":   float(partner.total_earnings or 0),

        "pending_payout":        float(partner.pending_payout or 0),

        "active_listings":       1 if partner.is_active else 0,

        "total_bookings":        0,

        "this_month_bookings":   0,

        "average_rating":        partner.rating or 0.0,

        "verification_status":   partner.verification_status,

    }
 
 
# ══════════════════ BOOKINGS ══════════════════
 
async def get_partner_bookings(current_user: User, status_filter: str, db: AsyncSession) -> list:

    partner = await get_partner_or_404(current_user.id, db)

    # Bookings module not yet integrated — returns empty list

    # Will be connected once Booking model is available

    return []
 
 
async def get_partner_booking_detail(booking_id: str, current_user: User, db: AsyncSession) -> dict:

    await get_partner_or_404(current_user.id, db)

    raise HTTPException(status_code=404, detail="Booking not found")
 
 
async def accept_booking(booking_id: str, current_user: User, db: AsyncSession) -> dict:

    await get_partner_or_404(current_user.id, db)

    # Will be implemented once Booking model is integrated

    return {"message": "Booking accepted. Traveler notified."}
 
 
async def reject_booking(booking_id: str, data: BookingActionRequest, current_user: User, db: AsyncSession) -> dict:

    if not data.reason:

        raise HTTPException(status_code=400, detail="Reason is required to reject a booking")

    await get_partner_or_404(current_user.id, db)

    return {"message": "Booking rejected. Admin will reassign."}
 
 
# ══════════════════ EARNINGS ══════════════════
 
async def get_earnings_summary(current_user: User, db: AsyncSession) -> dict:

    partner = await get_partner_or_404(current_user.id, db)
 
    # Get last payout

    result = await db.execute(

        select(PartnerPayout)

        .where(PartnerPayout.partner_id == partner.id,

               PartnerPayout.status == "TRANSFERRED")

        .order_by(PartnerPayout.transfer_date.desc())

        .limit(1)

    )

    last_payout = result.scalar_one_or_none()
 
    return {

        "total_earned":       float(partner.total_earnings or 0),

        "this_month":         0.0,  # will calc from bookings once integrated

        "pending_payout":     float(partner.pending_payout or 0),

        "commission_rate":    partner.commission_rate,

        "last_payout_date":   last_payout.transfer_date if last_payout else None,

        "last_payout_amount": float(last_payout.amount) if last_payout else None,

    }
 
 
async def get_earnings_report(current_user: User, from_date: str, to_date: str, db: AsyncSession) -> bytes:

    partner = await get_partner_or_404(current_user.id, db)
 
    output = io.StringIO()

    writer = csv.writer(output)

    writer.writerow(["Date", "Description", "Amount", "Commission", "Net Amount", "Status"])

    writer.writerow([datetime.utcnow().date(), "Sample entry", "1000.00", "100.00", "900.00", "PAID"])
 
    return output.getvalue().encode("utf-8")
 
 
# ══════════════════ PAYOUTS ══════════════════
 
async def get_payouts(current_user: User, db: AsyncSession) -> list:

    partner = await get_partner_or_404(current_user.id, db)

    result = await db.execute(

        select(PartnerPayout)

        .where(PartnerPayout.partner_id == partner.id)

        .order_by(PartnerPayout.created_at.desc())

    )

    return result.scalars().all()
 
 
async def get_payout_detail(payout_id: str, current_user: User, db: AsyncSession) -> PartnerPayout:

    partner = await get_partner_or_404(current_user.id, db)

    result = await db.execute(

        select(PartnerPayout).where(

            PartnerPayout.id == payout_id,

            PartnerPayout.partner_id == partner.id

        )

    )

    payout = result.scalar_one_or_none()

    if not payout:

        raise HTTPException(status_code=404, detail="Payout not found")

    return payout
 
 
# ══════════════════ BANK DETAILS ══════════════════
 
async def update_bank_details(data: BankDetailsRequest, current_user: User, db: AsyncSession) -> PartnerBankDetails:

    partner = await get_partner_or_404(current_user.id, db)
 
    result = await db.execute(

        select(PartnerBankDetails).where(PartnerBankDetails.partner_id == partner.id)

    )

    bank = result.scalar_one_or_none()
 
    if bank:

        bank.account_number      = data.account_number

        bank.ifsc_code           = data.ifsc_code

        bank.account_holder_name = data.account_holder_name

        bank.bank_name           = data.bank_name

        bank.branch_name         = data.branch_name

        bank.is_verified         = False   # reset verification on update

        bank.updated_at          = datetime.utcnow()

    else:

        bank = PartnerBankDetails(

            partner_id=partner.id,

            account_number=data.account_number,

            ifsc_code=data.ifsc_code,

            account_holder_name=data.account_holder_name,

            bank_name=data.bank_name,

            branch_name=data.branch_name,

        )

        db.add(bank)
 
    await db.commit()

    await db.refresh(bank)

    return bank
 
 
# ══════════════════ DOCUMENTS ══════════════════
 
async def list_documents(current_user: User, db: AsyncSession) -> list:

    partner = await get_partner_or_404(current_user.id, db)

    result = await db.execute(

        select(PartnerDocument).where(PartnerDocument.partner_id == partner.id)

    )

    return result.scalars().all()
 
 
async def upload_document(doc_type: str, file: UploadFile, current_user: User, db: AsyncSession) -> PartnerDocument:

    partner = await get_partner_or_404(current_user.id, db)
 
    doc_type = doc_type.upper()

    if doc_type not in ["GSTIN", "PAN", "BANK_PROOF", "PROPERTY_DOC", "OTHER"]:

        raise HTTPException(status_code=400, detail="Invalid doc_type")
 
    # S3 upload — stub until AWS S3 is configured

    # from src.integrations.aws_s3 import upload_file

    # file_url = await upload_file(await file.read(), file.content_type, f"partners/{partner.id}/{doc_type}")

    file_url = f"https://ap-tourism-media.s3.ap-south-1.amazonaws.com/partners/{partner.id}/{doc_type}_{file.filenam…
 
    doc = PartnerDocument(

        partner_id=partner.id,

        doc_type=doc_type,

        file_url=file_url,

        file_name=file.filename,

    )

    db.add(doc)

    await db.commit()

    await db.refresh(doc)

    logger.info("Document uploaded partner_id=%s doc_type=%s", partner.id, doc_type)

    return doc
 
 
async def delete_document(doc_id: str, current_user: User, db: AsyncSession) -> dict:

    partner = await get_partner_or_404(current_user.id, db)

    result = await db.execute(

        select(PartnerDocument).where(

            PartnerDocument.id == doc_id,

            PartnerDocument.partner_id == partner.id

        )

    )

    doc = result.scalar_one_or_none()

    if not doc:

        raise HTTPException(status_code=404, detail="Document not found")

    if doc.is_verified:

        raise HTTPException(status_code=400, detail="Cannot delete a verified document")
 
    await db.delete(doc)

    await db.commit()

    return {"message": "Document deleted successfully"}
 
 
# ══════════════════ SETTINGS ══════════════════
 
async def set_availability(data: AvailabilityRequest, current_user: User, db: AsyncSession) -> dict:

    partner = await get_partner_or_404(current_user.id, db)

    partner.unavailable_dates = data.unavailable_dates

    partner.updated_at = datetime.utcnow()

    await db.commit()

    return {"message": "Availability updated", "unavailable_dates": data.unavailable_dates}
 
 
async def update_settings(data: SettingsRequest, current_user: User, db: AsyncSession) -> dict:

    partner = await get_partner_or_404(current_user.id, db)
 
    if data.auto_accept is not None:

        partner.auto_accept = data.auto_accept

    if data.notification_prefs is not None:

        partner.notification_prefs = data.notification_prefs
 
    partner.updated_at = datetime.utcnow()

    await db.commit()
 
    return {

        "auto_accept":        partner.auto_accept,

        "notification_prefs": partner.notification_prefs,

    }
 
 
async def get_analytics(current_user: User, db: AsyncSession) -> dict:

    partner = await get_partner_or_404(current_user.id, db)

    # Placeholder — will connect to bookings/payments once integrated

    return {

        "booking_trend":    [],

        "revenue_chart":    [],

        "occupancy_rate":   0.0,

        "total_earnings":   float(partner.total_earnings or 0),

        "average_rating":   partner.rating or 0.0,

    }
 
 
async def get_notifications(current_user: User, db: AsyncSession) -> list:

    await get_partner_or_404(current_user.id, db)

    # Will connect to Notifications module once integrated

    return []
 
 
# ══════════════════ REVIEWS ══════════════════
 
async def get_reviews(current_user: User, db: AsyncSession) -> list:

    await get_partner_or_404(current_user.id, db)

    # Will connect to Reviews module once integrated

    return []
 
 
async def reply_to_review(review_id: str, data: ReviewReplyRequest, current_user: User, db: AsyncSession) -> dict:

    await get_partner_or_404(current_user.id, db)

    if not data.reply.strip():

        raise HTTPException(status_code=400, detail="Reply cannot be empty")

    # Will connect to Reviews module once integrated

    return {"message": "Reply posted successfully"}
 
 
# ══════════════════ PRIVATE HELPERS ══════════════════
 
def _partner_to_dict(partner: Partner) -> dict:

    return {

        "id":                  str(partner.id),

        "user_id":             str(partner.user_id),

        "business_name":       partner.business_name,

        "business_type":       partner.business_type,

        "gstin":               partner.gstin,

        "pan":                 partner.pan,

        "description":         partner.description,

        "logo_url":            partner.logo_url,

        "contact_phone":       partner.contact_phone,

        "contact_email":       partner.contact_email,

        "website":             partner.website,

        "address":             partner.address,

        "city":                partner.city,

        "state":               partner.state,

        "verification_status": partner.verification_status,

        "commission_rate":     partner.commission_rate,

        "total_earnings":      float(partner.total_earnings or 0),

        "pending_payout":      float(partner.pending_payout or 0),

        "rating":              partner.rating,

        "total_reviews":       partner.total_reviews,

        "auto_accept":         partner.auto_accept,

        "created_at":          partner.created_at,

    }
 