"""

api/v1/endpoints/partners.py

Partners module — all 20 endpoints.

Profile:

  POST /partners/register

  GET  /partners/me

  GET  /partners/me/dashboard

Bookings:

  GET  /partners/me/bookings

  GET  /partners/me/bookings/{id}

  PUT  /partners/me/bookings/{id}/accept

  PUT  /partners/me/bookings/{id}/reject

Earnings:

  GET  /partners/me/earnings

  GET  /partners/me/earnings/report

Payouts:

  GET  /partners/me/payouts

  GET  /partners/me/payouts/{id}

  PUT  /partners/me/bank-details

Documents:

  GET  /partners/me/documents

  POST /partners/me/documents

  DELETE /partners/me/documents/{id}

Settings:

  PUT  /partners/me/availability

  PUT  /partners/me/settings

  GET  /partners/me/analytics

  GET  /partners/me/notifications

Reviews:

  GET  /partners/me/reviews

  POST /partners/me/reviews/{id}/reply

"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File

from fastapi.responses import Response

from sqlalchemy.ext.asyncio import AsyncSession

from typing import Optional

from src.core.database import get_db

from src.api.deps.auth import get_current_user, get_partner_user

from src.models.user import User

from src.schemas.partner import (

    PartnerRegisterRequest, PartnerUpdateRequest,

    BankDetailsRequest, AvailabilityRequest,

    SettingsRequest, ReviewReplyRequest, BookingActionRequest,

    PayoutResponse, DocumentResponse, BankDetailsResponse

)

from src.common.responses import APIResponse

from src.services import partner_service

router = APIRouter(prefix="/partners", tags=["Partners"])


# ══════════════════ PROFILE ══════════════════

@router.post("/register", response_model=APIResponse, status_code=201,

             summary="Register as partner")

async def register(

    data: PartnerRegisterRequest,

    current_user: User = Depends(get_current_user),  # any logged-in user can apply

    db: AsyncSession = Depends(get_db)

):

    """

    Register as a partner. Sets status = APPLIED.

    business_type: HOTEL | VEHICLE | GUIDE

    """

    partner = await partner_service.register_partner(data, current_user, db)

    return APIResponse.success(

        message="Partner registered. Awaiting admin verification.",

        data=partner_service._partner_to_dict(partner)

    )


@router.get("/me", response_model=APIResponse, summary="Get partner profile")

async def get_profile(

    current_user: User = Depends(get_partner_user),

    db: AsyncSession = Depends(get_db)

):

    """Partner profile with verification_status, commission_rate, total_earnings."""

    data = await partner_service.get_my_profile(current_user, db)

    return APIResponse.success(message="Profile fetched", data=data)


@router.get("/me/dashboard", response_model=APIResponse, summary="Partner dashboard stats")

async def get_dashboard(

    current_user: User = Depends(get_partner_user),

    db: AsyncSession = Depends(get_db)

):

    """Dashboard stats: today's bookings, this month's earnings, pending payouts, active listings."""

    data = await partner_service.get_dashboard(current_user, db)

    return APIResponse.success(message="Dashboard fetched", data=data)


# ══════════════════ BOOKINGS ══════════════════

@router.get("/me/bookings", response_model=APIResponse, summary="Partner bookings")

async def get_bookings(

    status: Optional[str] = Query(None, description="Filter: PENDING | CONFIRMED | COMPLETED | CANCELLED"),

    current_user: User = Depends(get_partner_user),

    db: AsyncSession = Depends(get_db)

):

    """Bookings assigned to this partner. Filter by status."""

    bookings = await partner_service.get_partner_bookings(current_user, status, db)

    return APIResponse.success(message=f"{len(bookings)} bookings found", data=bookings)


@router.get("/me/bookings/{booking_id}", response_model=APIResponse, summary="Booking detail")

async def get_booking_detail(

    booking_id: str,

    current_user: User = Depends(get_partner_user),

    db: AsyncSession = Depends(get_db)

):

    """Specific booking detail with traveler details and special requirements."""

    data = await partner_service.get_partner_booking_detail(booking_id, current_user, db)

    return APIResponse.success(message="Booking fetched", data=data)


@router.put("/me/bookings/{booking_id}/accept", response_model=APIResponse, summary="Accept booking")

async def accept_booking(

    booking_id: str,

    current_user: User = Depends(get_partner_user),

    db: AsyncSession = Depends(get_db)

):

    """Accept booking assignment. Traveler is notified via SMS."""

    result = await partner_service.accept_booking(booking_id, current_user, db)

    return APIResponse.success(message=result["message"])


@router.put("/me/bookings/{booking_id}/reject", response_model=APIResponse, summary="Reject booking")

async def reject_booking(

    booking_id: str,

    data: BookingActionRequest,

    current_user: User = Depends(get_partner_user),

    db: AsyncSession = Depends(get_db)

):

    """Reject booking. Reason required. Admin will reassign."""

    result = await partner_service.reject_booking(booking_id, data, current_user, db)

    return APIResponse.success(message=result["message"])


# ══════════════════ EARNINGS ══════════════════

@router.get("/me/earnings", response_model=APIResponse, summary="Earnings summary")

async def get_earnings(

    current_user: User = Depends(get_partner_user),

    db: AsyncSession = Depends(get_db)

):

    """Earnings summary: total_earned, this_month, pending_payout, commission_rate."""

    data = await partner_service.get_earnings_summary(current_user, db)

    return APIResponse.success(message="Earnings fetched", data=data)


@router.get("/me/earnings/report", summary="Download earnings report CSV")

async def get_earnings_report(

    from_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),

    to_date:   Optional[str] = Query(None, description="End date YYYY-MM-DD"),

    current_user: User = Depends(get_partner_user),

    db: AsyncSession = Depends(get_db)

):

    """Download earnings report as CSV with date filters."""

    csv_bytes = await partner_service.get_earnings_report(current_user, from_date, to_date, db)

    return Response(

        content=csv_bytes,

        media_type="text/csv",

        headers={"Content-Disposition": "attachment; filename=earnings_report.csv"}

    )


# ══════════════════ PAYOUTS ══════════════════

@router.get("/me/payouts", response_model=APIResponse, summary="Payout history")

async def get_payouts(

    current_user: User = Depends(get_partner_user),

    db: AsyncSession = Depends(get_db)

):

    """Payout history: amount, bank_account, status (PENDING/TRANSFERRED), transfer_date."""

    payouts = await partner_service.get_payouts(current_user, db)

    data = [PayoutResponse.model_validate(p).model_dump() for p in payouts]

    return APIResponse.success(message=f"{len(data)} payouts found", data=data)


@router.get("/me/payouts/{payout_id}", response_model=APIResponse, summary="Single payout detail")

async def get_payout_detail(

    payout_id: str,

    current_user: User = Depends(get_partner_user),

    db: AsyncSession = Depends(get_db)

):

    """Single payout detail by ID."""

    payout = await partner_service.get_payout_detail(payout_id, current_user, db)

    return APIResponse.success(

        message="Payout fetched",

        data=PayoutResponse.model_validate(payout).model_dump()

    )


@router.put("/me/bank-details", response_model=APIResponse, summary="Update bank details")

async def update_bank_details(

    data: BankDetailsRequest,

    current_user: User = Depends(get_partner_user),

    db: AsyncSession = Depends(get_db)

):

    """Update bank account details for payouts. Resets verification status."""

    bank = await partner_service.update_bank_details(data, current_user, db)

    return APIResponse.success(

        message="Bank details updated. Pending admin verification.",

        data=BankDetailsResponse.model_validate(bank).model_dump()

    )


# ══════════════════ DOCUMENTS ══════════════════

@router.get("/me/documents", response_model=APIResponse, summary="List KYC documents")

async def list_documents(

    current_user: User = Depends(get_partner_user),

    db: AsyncSession = Depends(get_db)

):

    """List all uploaded KYC documents with verification status."""

    docs = await partner_service.list_documents(current_user, db)

    data = [DocumentResponse.model_validate(d).model_dump() for d in docs]

    return APIResponse.success(message=f"{len(data)} documents found", data=data)


@router.post("/me/documents", response_model=APIResponse, status_code=201,

             summary="Upload KYC document")

async def upload_document(

    doc_type: str = Query(..., description="GSTIN | PAN | BANK_PROOF | PROPERTY_DOC | OTHER"),

    file: UploadFile = File(...),

    current_user: User = Depends(get_partner_user),

    db: AsyncSession = Depends(get_db)

):

    """Upload a KYC document. Stored in AWS S3."""

    doc = await partner_service.upload_document(doc_type, file, current_user, db)

    return APIResponse.success(

        message="Document uploaded successfully",

        data=DocumentResponse.model_validate(doc).model_dump()

    )


@router.delete("/me/documents/{doc_id}", response_model=APIResponse, summary="Delete document")

async def delete_document(

    doc_id: str,

    current_user: User = Depends(get_partner_user),

    db: AsyncSession = Depends(get_db)

):

    """Delete a document. Only allowed if not yet verified."""

    result = await partner_service.delete_document(doc_id, current_user, db)

    return APIResponse.success(message=result["message"])


# ══════════════════ SETTINGS ══════════════════

@router.put("/me/availability", response_model=APIResponse, summary="Set unavailable dates")

async def set_availability(

    data: AvailabilityRequest,

    current_user: User = Depends(get_partner_user),

    db: AsyncSession = Depends(get_db)

):

    """Set unavailable dates. Format: ['2024-12-25', '2024-12-26']"""

    result = await partner_service.set_availability(data, current_user, db)

    return APIResponse.success(message=result["message"], data=result)


@router.put("/me/settings", response_model=APIResponse, summary="Update partner settings")

async def update_settings(

    data: SettingsRequest,

    current_user: User = Depends(get_partner_user),

    db: AsyncSession = Depends(get_db)

):

    """Update: auto_accept bookings, notification preferences."""

    result = await partner_service.update_settings(data, current_user, db)

    return APIResponse.success(message="Settings updated", data=result)


@router.get("/me/analytics", response_model=APIResponse, summary="Partner analytics")

async def get_analytics(

    current_user: User = Depends(get_partner_user),

    db: AsyncSession = Depends(get_db)

):

    """Partner analytics: booking trends, revenue chart, occupancy rate."""

    data = await partner_service.get_analytics(current_user, db)

    return APIResponse.success(message="Analytics fetched", data=data)


@router.get("/me/notifications", response_model=APIResponse, summary="Partner notifications")

async def get_notifications(

    current_user: User = Depends(get_partner_user),

    db: AsyncSession = Depends(get_db)

):

    """Partner notifications: booking requests, payment received, etc."""

    data = await partner_service.get_notifications(current_user, db)

    return APIResponse.success(message=f"{len(data)} notifications", data=data)


# ══════════════════ REVIEWS ══════════════════

@router.get("/my-reviews", response_model=APIResponse, summary="Reviews received")

async def get_reviews(

    current_user: User = Depends(get_partner_user),

    db: AsyncSession = Depends(get_db)

):

    """Reviews received from travelers sorted by date."""

    data = await partner_service.get_reviews(current_user, db)

    return APIResponse.success(message=f"{len(data)} reviews", data=data)


@router.post("/me/reviews/{review_id}/reply", response_model=APIResponse, summary="Reply to review")

async def reply_to_review(

    review_id: str,

    data: ReviewReplyRequest,

    current_user: User = Depends(get_partner_user),

    db: AsyncSession = Depends(get_db)

):

    """Reply to a traveler review. Reply stored as review_reply."""

    result = await partner_service.reply_to_review(review_id, data, current_user, db)

    return APIResponse.success(message=result["message"])
 