import logging
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, Query
from sqlalchemy.orm import Session

from src.api.deps.database import get_db
from src.schemas.partner import (
    PartnerRegisterSchema, PartnerUpdateSchema, PartnerResponseSchema,
    BankDetailsSchema, AvailabilityUpdateSchema, SettingsUpdateSchema,
    DocumentResponseSchema, PayoutResponseSchema
)
import src.services.partner_service as partner_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/partner", tags=["Partner"])


def success(data, message: str = "") -> dict:
    return {"success": True, "data": data, "message": message}


# NOTE: user_id=1 is temporary until LEV148 completes auth module


@router.post("/register")
async def register_partner(
    data: PartnerRegisterSchema,
    db: Session = Depends(get_db)
):
    result = await partner_service.register_partner(db, data)
    return success(PartnerResponseSchema.from_orm(result), "Partner registered successfully")


@router.get("/me")
async def get_my_profile(db: Session = Depends(get_db)):
    result = await partner_service.get_partner_profile(db, user_id=1)
    return success(PartnerResponseSchema.from_orm(result))


@router.put("/me")
async def update_my_profile(
    data: PartnerUpdateSchema,
    db: Session = Depends(get_db)
):
    result = await partner_service.update_partner_profile(db, 1, data)
    return success(PartnerResponseSchema.from_orm(result), "Profile updated")


@router.get("/me/dashboard")
async def get_dashboard(db: Session = Depends(get_db)):
    result = await partner_service.get_dashboard_stats(db, user_id=1)
    return success(result)


@router.get("/me/bookings")
async def list_bookings(
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db)
):
    result = await partner_service.get_partner_bookings(db, 1, status, page, limit)
    return success(result)


@router.get("/me/bookings/{booking_id}")
async def get_booking_detail(
    booking_id: int,
    db: Session = Depends(get_db)
):
    result = await partner_service.get_partner_booking_detail(db, 1, booking_id)
    return success(result)


@router.put("/me/bookings/{booking_id}/accept")
async def accept_booking(
    booking_id: int,
    db: Session = Depends(get_db)
):
    result = await partner_service.accept_booking(db, 1, booking_id)
    return success(result, "Booking accepted")


@router.put("/me/bookings/{booking_id}/reject")
async def reject_booking(
    booking_id: int,
    db: Session = Depends(get_db)
):
    result = await partner_service.reject_booking(db, 1, booking_id)
    return success(result, "Booking rejected")


@router.get("/me/earnings")
async def get_earnings(db: Session = Depends(get_db)):
    result = await partner_service.get_partner_earnings(db, user_id=1)
    return success(result)


@router.get("/me/earnings/report")
async def download_earnings_report(db: Session = Depends(get_db)):
    result = await partner_service.get_earnings_report(db, user_id=1)
    return success(result)


@router.get("/me/payouts")
async def list_payouts(
    page: int = Query(1, ge=1),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db)
):
    result = await partner_service.get_partner_payouts(db, user_id=1, page=page, limit=limit)
    return success(result)


@router.get("/me/payouts/{payout_id}")
async def get_payout(
    payout_id: int,
    db: Session = Depends(get_db)
):
    result = await partner_service.get_payout_detail(db, payout_id)
    return success(result)


@router.put("/me/bank-details")
async def update_bank_details(
    data: BankDetailsSchema,
    db: Session = Depends(get_db)
):
    result = await partner_service.update_bank_details(db, 1, data)
    return success(PartnerResponseSchema.from_orm(result), "Bank details updated")


@router.get("/me/documents")
async def list_documents(db: Session = Depends(get_db)):
    result = await partner_service.get_documents(db, user_id=1)
    return success(result)


@router.post("/me/documents")
async def upload_document(
    document_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    file_url = f"https://s3.amazonaws.com/ap-tourism/partner-documents/{file.filename}"
    result = await partner_service.upload_document(db, 1, document_type, file_url)
    return success(DocumentResponseSchema.from_orm(result), "Document uploaded")


@router.delete("/me/documents/{doc_id}")
async def delete_document(
    doc_id: int,
    db: Session = Depends(get_db)
):
    result = await partner_service.delete_document(db, 1, doc_id)
    return success(result)


@router.put("/me/availability")
async def update_availability(
    data: AvailabilityUpdateSchema,
    db: Session = Depends(get_db)
):
    result = await partner_service.update_availability(db, 1, data)
    return success({"unavailable_dates": result.unavailable_dates}, "Availability updated")


@router.put("/me/settings")
async def update_settings(
    data: SettingsUpdateSchema,
    db: Session = Depends(get_db)
):
    result = await partner_service.update_settings(db, 1, data)
    return success(PartnerResponseSchema.from_orm(result), "Settings updated")


@router.get("/me/analytics")
async def get_analytics(db: Session = Depends(get_db)):
    result = await partner_service.get_analytics(db, user_id=1)
    return success(result)


@router.get("/me/notifications")
async def get_notifications(
    page: int = Query(1, ge=1),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db)
):
    result = await partner_service.get_partner_notifications(db, 1, page, limit)
    return success(result)


@router.get("/me/reviews")
async def get_reviews(
    page: int = Query(1, ge=1),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db)
):
    result = await partner_service.get_partner_reviews(db, 1, page, limit)
    return success(result)


@router.post("/me/reviews/{review_id}/reply")
async def reply_to_review(
    review_id: int,
    data: dict,
    db: Session = Depends(get_db)
):
    result = await partner_service.reply_to_review(db, 1, review_id, data)
    return success(result)
