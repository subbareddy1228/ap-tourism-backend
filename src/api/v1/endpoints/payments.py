from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database import get_db
from src.schemas.payment import (
    InitiatePaymentRequest, InitiatePaymentResponse,
    VerifyPaymentRequest, VerifyPaymentResponse,
    PaymentHistoryResponse, TransactionOut,
    PaymentMethodsResponse,
    ValidateUPIRequest, ValidateUPIResponse,
    SavedCardsResponse, SaveCardRequest, SaveCardResponse, DeleteCardResponse,
    RefundRequest, RefundResponse, RefundsListResponse,
    PayLaterCheckRequest, PayLaterCheckResponse,
    PayLaterApplyRequest, PayLaterApplyResponse,
    WebhookPayload,
)
from src.services.payment_service import (
    get_payment_methods,
    initiate_payment,
    verify_payment,
    get_payment_history,
    get_transaction,
    validate_upi,
    get_saved_cards,
    save_card,
    delete_saved_card,
    request_refund,
    get_refund,
    get_refunds,
    check_pay_later,
    apply_pay_later,
    handle_webhook,
)

router = APIRouter(prefix="/payment", tags=["Module 12 - Payments"])


# ─── GET /methods ────────────────────────────
@router.get("/methods", response_model=PaymentMethodsResponse, summary="Get Payment Methods")
def payment_methods():
    return get_payment_methods()


# ─── POST /initiate ──────────────────────────
@router.post("/initiate", response_model=InitiatePaymentResponse, summary="Initiate Payment")
def initiate(data: InitiatePaymentRequest, db: Session = Depends(get_db)):
    return initiate_payment(db, data)


# ─── POST /verify ────────────────────────────
@router.post("/verify", response_model=VerifyPaymentResponse, summary="Verify Payment")
def verify(data: VerifyPaymentRequest, db: Session = Depends(get_db)):
    return verify_payment(db, data)


# ─── GET /history ────────────────────────────
@router.get("/history", response_model=PaymentHistoryResponse, summary="Payment History")
def history(user_id: UUID, db: Session = Depends(get_db)):
    return get_payment_history(db, user_id)


# ─── POST /validate-upi ──────────────────────
@router.post("/validate-upi", response_model=ValidateUPIResponse, summary="Validate UPI")
def validate_upi_id(data: ValidateUPIRequest):
    return validate_upi(data)


# ─── GET /saved-cards ────────────────────────
@router.get("/saved-cards", response_model=SavedCardsResponse, summary="Get Saved Cards")
def saved_cards(user_id: UUID, db: Session = Depends(get_db)):
    return get_saved_cards(db, user_id)


# ─── POST /saved-cards ───────────────────────
@router.post("/saved-cards", response_model=SaveCardResponse, summary="Save Card")
def add_card(data: SaveCardRequest, db: Session = Depends(get_db)):
    return save_card(db, data)


# ─── DELETE /saved-cards/{card_id} ───────────
@router.delete("/saved-cards/{card_id}", response_model=DeleteCardResponse, summary="Delete Saved Card")
def remove_card(card_id: UUID, user_id: UUID, db: Session = Depends(get_db)):
    return delete_saved_card(db, card_id, user_id)


# ─── GET /refunds ────────────────────────────
@router.get("/refunds", response_model=RefundsListResponse, summary="Get Refunds")
def refunds_list(user_id: UUID, db: Session = Depends(get_db)):
    return get_refunds(db, user_id)


# ─── POST /refund/request ────────────────────
@router.post("/refund/request", response_model=RefundResponse, summary="Request Refund")
def refund_request(data: RefundRequest, db: Session = Depends(get_db)):
    return request_refund(db, data)


# ─── GET /refund/{refund_id} ─────────────────
@router.get("/refund/{refund_id}", response_model=RefundResponse, summary="Get Refund")
def refund_detail(refund_id: UUID, db: Session = Depends(get_db)):
    return get_refund(db, refund_id)


# ─── POST /pay-later/check ───────────────────
@router.post("/pay-later/check", response_model=PayLaterCheckResponse, summary="Check Pay Later Eligibility")
def pay_later_check(data: PayLaterCheckRequest):
    return check_pay_later(data)


# ─── POST /pay-later/apply ───────────────────
@router.post("/pay-later/apply", response_model=PayLaterApplyResponse, summary="Apply Pay Later")
def pay_later_apply(data: PayLaterApplyRequest, db: Session = Depends(get_db)):
    return apply_pay_later(db, data)


# ─── POST /webhook/razorpay ──────────────────
@router.post("/webhook/razorpay", summary="Razorpay Webhook")
def razorpay_webhook(payload: WebhookPayload, db: Session = Depends(get_db)):
    return handle_webhook(db, payload.dict())


# ─── GET /{transaction_id} ───────────────────
@router.get("/{transaction_id}", response_model=TransactionOut, summary="Get Transaction")
def transaction_detail(transaction_id: UUID, db: Session = Depends(get_db)):
    txn = get_transaction(db, transaction_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    return txn