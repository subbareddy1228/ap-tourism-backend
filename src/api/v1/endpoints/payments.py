import math, logging
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from src.database import get_db
from src.api.deps import get_current_user  # deps folder __init__.py
from src.schemas.payment import *
from src.services.payment_service import PaymentService, RefundService, PaymentMethodService, PayLaterService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/payment", tags=["Module 12 - Payments"])

def ok(data, message=""):
    return {"success": True, "data": data, "message": message}

def err(message, code):
    raise HTTPException(status_code=code, detail={"success": False, "error": message, "code": code})

@router.get("/history")
def payment_history(page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db), user=Depends(get_current_user)):
    total, items = PaymentService.get_history(db, user.id, page, limit)
    pages = math.ceil(total / limit) if total else 1
    data = PaymentHistoryData(data=[PaymentHistoryItem.from_orm(i) for i in items], total=total, page=page, pages=pages, limit=limit)
    return ok(data, "Payment history fetched.")

@router.get("/methods")
def get_payment_methods():
    return ok(PaymentMethodService.get_methods(), "Payment methods fetched.")

@router.post("/validate-upi")
def validate_upi(body: UpiValidateRequest, user=Depends(get_current_user)):
    result = PaymentMethodService.validate_upi(body.upi_id)
    return ok(UpiValidateData(**result), "UPI validation completed.")

@router.get("/saved-cards")
def get_saved_cards(db: Session = Depends(get_db), user=Depends(get_current_user)):
    cards = PaymentMethodService.get_saved_cards(db, user.id)
    return ok([SavedCardData.from_orm(c) for c in cards], "Saved cards fetched.")

@router.post("/saved-cards", status_code=status.HTTP_201_CREATED)
def save_card(body: SaveCardRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    card = PaymentMethodService.save_card(db, user.id, body)
    return ok(SavedCardData.from_orm(card), "Card saved successfully.")

@router.delete("/saved-cards/{card_id}")
def delete_saved_card(card_id: UUID, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try: PaymentMethodService.delete_card(db, user.id, card_id)
    except ValueError as e: err(str(e), 404)
    return ok(None, "Saved card removed.")

@router.get("/refunds")
def get_refunds(db: Session = Depends(get_db), user=Depends(get_current_user)):
    items = RefundService.get_user_refunds(db, user.id)
    return ok(RefundListData(data=[RefundData.from_orm(r) for r in items], total=len(items)), "Refunds fetched.")

@router.post("/refund/request", status_code=status.HTTP_201_CREATED)
def request_refund(body: RefundRequestSchema, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try: refund = RefundService.request_refund(db, user.id, body)
    except ValueError as e: err(str(e), 400)
    return ok(RefundData.from_orm(refund), "Refund initiated successfully.")

@router.get("/refund/{refund_id}")
def get_refund(refund_id: UUID, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try: refund = RefundService.get_refund(db, user.id, refund_id)
    except ValueError as e: err(str(e), 404)
    return ok(RefundData.from_orm(refund), "Refund detail fetched.")

@router.post("/pay-later/check")
def check_pay_later(body: PayLaterCheckRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    result = PayLaterService.check_eligibility(db, user.id, body)
    return ok(PayLaterCheckData(**result), "Pay Later eligibility checked.")

@router.post("/pay-later/apply", status_code=status.HTTP_201_CREATED)
def apply_pay_later(body: PayLaterApplyRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try: tx, due_date = PayLaterService.apply_pay_later(db, user.id, body)
    except ValueError as e: err(str(e), 400)
    return ok(PayLaterApplyData(transaction_id=tx.id, due_date=due_date, amount=tx.amount), f"Pay Later applied. Due by {due_date.strftime('%d %b %Y')}.")

@router.post("/webhook/razorpay", include_in_schema=False)
async def razorpay_webhook(request: Request, x_razorpay_signature: str = Header(..., alias="X-Razorpay-Signature"), db: Session = Depends(get_db)):
    payload = await request.body()
    try: result = PaymentService.handle_webhook(db, payload, x_razorpay_signature)
    except ValueError as e: err(str(e), 400)
    return {"success": True, "status": result["status"]}

@router.post("/initiate", status_code=status.HTTP_201_CREATED)
def initiate_payment(body: PaymentInitiateRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try: tx = PaymentService.initiate(db, user.id, body)
    except ValueError as e: err(str(e), 400)
    from src.core.config import settings
    data = PaymentInitiateData(transaction_id=tx.id, razorpay_order_id=tx.razorpay_order_id, key_id=settings.RAZORPAY_KEY_ID, amount=tx.amount, currency=tx.currency, status=tx.status)
    return ok(data, "Payment initiated.")

@router.post("/verify")
def verify_payment(body: PaymentVerifyRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try: tx = PaymentService.verify(db, user.id, body)
    except ValueError as e: err(str(e), 400)
    return ok(PaymentVerifyData(transaction_id=tx.id, status=tx.status, booking_id=tx.booking_id), "Payment verified. Booking confirmed.")

@router.get("/{transaction_id}")   # ← MUST BE LAST
def get_transaction(transaction_id: UUID, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try: tx = PaymentService.get_transaction(db, user.id, transaction_id)
    except ValueError as e: err(str(e), 404)
    return ok(TransactionData.from_orm(tx), "Payment detail fetched.")