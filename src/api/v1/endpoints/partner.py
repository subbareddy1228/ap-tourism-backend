import logging
import time
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from src.api.deps.database import get_db
from src.schemas.partner import (
    PartnerRegisterSchema, PartnerUpdateSchema, PartnerResponseSchema,
    BankDetailsSchema, AvailabilityUpdateSchema, PartnerSettingsSchema,
    ReviewReplySchema, BookingRejectSchema, SuccessResponse
)
import src.services.partner_service as partner_service
# Auth dependencies — provided by LEV148
#from src.core.dependencies import get_current_user, require_partner

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/partner", tags=["Partner"])


# ─── Helper ───────────────────────────────────────────────────────────────────

def success(data, message: str = "") -> dict:
    return {"success": True, "data": data, "message": message}


# ─── Registration ─────────────────────────────────────────────────────────────

# Change this
@router.post("/register")
def register_partner(
    data: PartnerRegisterSchema,
    db: Session = Depends(get_db)
):
    result = partner_service.register_partner(db, data)
    return success(PartnerResponseSchema.from_orm(result), "Partner registered successfully")


# ─── Profile ──────────────────────────────────────────────────────────────────

@router.get("/me")
def get_my_profile(
    db: Session = Depends(get_db),
    #user=Depends(require_partner)
):
    """Partner profile with verification_status, commission_rate, total_earnings."""
    result = partner_service.get_partner_profile(db, user_id=1)
    return success(PartnerResponseSchema.from_orm(result))


@router.put("/me")
def update_my_profile(
    data: PartnerUpdateSchema,
    db: Session = Depends(get_db),
    #user=Depends(require_partner)
):
    result = partner_service.update_partner_profile(db, 1,data)
    return success(PartnerResponseSchema.from_orm(result), "Profile updated")


@router.get("/me/dashboard")
def get_dashboard(
    db: Session = Depends(get_db),
    #user=Depends(require_partner)
):
    """Dashboard stats: today's bookings, this month's earnings, pending payouts, active listings."""
    result = partner_service.get_dashboard_stats(db, user_id=1)
    return success(result)


# ─── Bookings ─────────────────────────────────────────────────────────────────

@router.get("/me/bookings")
def list_bookings(
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
    #user=Depends(require_partner)
):
    """Bookings assigned to partner. Filter by status, date."""
    result = partner_service.get_partner_bookings(db,1, status, page, limit)
    return success(result)


@router.get("/me/bookings/{booking_id}")
def get_booking_detail(
    booking_id: int,
    db: Session = Depends(get_db),
    #user=Depends(require_partner)
):
    """Specific booking detail with traveler details and special requirements."""
    result = partner_service.get_partner_booking_detail(db, booking_id, 1)
    return success(result)


@router.put("/me/bookings/{booking_id}/accept")
def accept_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    #user=Depends(require_partner)
):
    """Accept booking assignment and notify traveler."""
    result = partner_service.accept_booking(db, booking_id, 1)
    return success(result, "Booking accepted")


@router.put("/me/bookings/{booking_id}/reject")
def reject_booking(
    booking_id: int,
    data: BookingRejectSchema,
    db: Session = Depends(get_db),
    #user=Depends(require_partner)
):
    """Reject booking; admin reassigns. Reason required."""
    result = partner_service.reject_booking(db, 1, booking_id)
    return success(result, "Booking rejected")


# ─── Earnings ─────────────────────────────────────────────────────────────────

@router.get("/me/earnings")
def get_earnings(
    db: Session = Depends(get_db),
    #user=Depends(require_partner)
):
    """Earnings summary: total_earned, this_month, pending_payout, commission_rate."""
    result = partner_service.get_earnings_summary(db,user_id=1)
    return success(result)


@router.get("/me/earnings/report")
def download_earnings_report(db: Session = Depends(get_db)):
    return {"success": True, "data": {"message": "Report available after LEV151 completes booking module"}}


# ─── Payouts ──────────────────────────────────────────────────────────────────

@router.get("/me/payouts")
def list_payouts(
    page: int = Query(1, ge=1),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
    #user=Depends(require_partner)
):
    """Payout history: amount, bank_account, status (PENDING/TRANSFERRED), transfer_date."""
    result = partner_service.get_payouts(db, user_id=1, page=page, limit=limit)
    return success(result)


@router.get("/me/payouts/{payout_id}")
def get_payout(
    payout_id: int,
    db: Session = Depends(get_db),
    #user=Depends(require_partner)
):
    """Single payout detail."""
    result = partner_service.get_payout_detail(db, user_id=1, payout_id=payout_id)

    return success(result)


# ─── Bank Details ─────────────────────────────────────────────────────────────

@router.put("/me/bank-details")
def update_bank_details(
    data: BankDetailsSchema,
    db: Session = Depends(get_db),
    #user=Depends(require_partner)
):
    """Update bank details: account_number, IFSC, account_holder_name."""
    result = partner_service.update_bank_details(db, 1,data)
    return success(PartnerResponseSchema.from_orm(result), "Bank details updated")


# ─── Documents ────────────────────────────────────────────────────────────────

@router.get("/me/documents")
def list_documents(
    db: Session = Depends(get_db),
    #user=Depends(require_partner)
):
    """List uploaded KYC documents with verification status."""
    result = partner_service.get_documents(db, user_id=1)
    return success(result)


@router.post("/me/documents")
def upload_document(
    document_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    #user=Depends(require_partner)
):
    """Upload KYC documents: GSTIN, PAN, bank_proof, property_doc. Stored in S3."""
    # TODO: upload file to S3 using s3_utils, get back the S3 URL
    # file_url = upload_to_s3(file, folder="partner-documents")
    file_url = f"https://s3.amazonaws.com/ap-tourism/partner-documents/{file.filename}"  # placeholder
    result = partner_service.upload_document(db,1, document_type, file_url)
    return success(result, "Document uploaded successfully")


@router.delete("/me/documents/{doc_id}")
def delete_document(
    doc_id: int,
    db: Session = Depends(get_db),
    #user=Depends(require_partner)
):
    """Delete document if not verified by admin."""
    result = partner_service.delete_document(db, user_id=1,doc_id=1)
    return success(result)


# ─── Settings ─────────────────────────────────────────────────────────────────

@router.put("/me/availability")
def update_availability(
    data: AvailabilityUpdateSchema,
    db: Session = Depends(get_db),
    #user=Depends(require_partner)
):
    """Set availability dates (mark unavailable dates)."""
    result = partner_service.update_availability(db,1, data)
    return success({"unavailable_dates": result.unavailable_dates}, "Availability updated")


@router.put("/me/settings")
def update_settings(
    data: PartnerSettingsSchema,
    db: Session = Depends(get_db),
    #user=Depends(require_partner)
):
    """Update partner settings: auto-accept bookings, notification preferences."""
    result = partner_service.update_settings(db,1, data)
    return success(PartnerResponseSchema.from_orm(result), "Settings updated")


@router.get("/me/analytics")
def get_analytics(
    db: Session = Depends(get_db),
    #user=Depends(require_partner)
):
    """Partner analytics: booking trends, revenue chart, occupancy rate."""
    result = partner_service.get_analytics(db,user_id=1)
    return success(result)


# ─── Notifications ────────────────────────────────────────────────────────────

@router.get("/me/notifications")
def get_notifications(
    page: int = Query(1, ge=1),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
    #user=Depends(require_partner)
):
    """Partner notifications: booking requests, payment received, etc."""
    result = partner_service.get_partner_notifications(db,1, page, limit)
    return success(result)


# ─── Reviews ──────────────────────────────────────────────────────────────────

@router.get("/me/reviews")
def get_reviews(
    page: int = Query(1, ge=1),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
    #user=Depends(require_partner)
):
    """Reviews received from travelers sorted by date."""
    result = partner_service.get_partner_reviews(db,1, page, limit)
    return success(result)


@router.post("/me/reviews/{review_id}/reply")
def reply_to_review(
    review_id: int,
    data: ReviewReplySchema,
    db: Session = Depends(get_db),
    #user=Depends(require_partner)
):
    """Reply to a review. Stored as review_reply."""
    result = partner_service.reply_to_review(db,1, review_id, data)
    return success(result, "Reply posted")