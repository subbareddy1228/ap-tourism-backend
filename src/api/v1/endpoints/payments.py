from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt

from src.database import get_db
from src.core.config import settings
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

# ─────────────────────────────────────────────
# JWT DEPENDENCY — extracts user_id from Bearer token
# ─────────────────────────────────────────────

security = HTTPBearer()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UUID:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token: user_id not found.")
        return UUID(user_id)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token.")


# ─── GET /methods (no auth needed) ──────────
@router.get("/methods", response_model=PaymentMethodsResponse, summary="Get Payment Methods")
async def payment_methods():
    return get_payment_methods()


# ─── POST /initiate ──────────────────────────
@router.post("/initiate", response_model=InitiatePaymentResponse, summary="Initiate Payment")
async def initiate(
    data: InitiatePaymentRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    data.user_id = user_id
    return await initiate_payment(db, data)


# ─── POST /verify ────────────────────────────
@router.post("/verify", response_model=VerifyPaymentResponse, summary="Verify Payment")
async def verify(
    data: VerifyPaymentRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    return await verify_payment(db, data)


# ─── GET /history ────────────────────────────
@router.get("/history", response_model=PaymentHistoryResponse, summary="Payment History")
async def history(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    return await get_payment_history(db, user_id)


# ─── POST /validate-upi ──────────────────────
@router.post("/validate-upi", response_model=ValidateUPIResponse, summary="Validate UPI")
async def validate_upi_id(
    data: ValidateUPIRequest,
    user_id: UUID = Depends(get_current_user_id),
):
    return validate_upi(data)


# ─── GET /saved-cards ────────────────────────
@router.get("/saved-cards", response_model=SavedCardsResponse, summary="Get Saved Cards")
async def saved_cards(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    return await get_saved_cards(db, user_id)


# ─── POST /saved-cards ───────────────────────
@router.post("/saved-cards", response_model=SaveCardResponse, summary="Save Card")
async def add_card(
    data: SaveCardRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    data.user_id = user_id
    return await save_card(db, data)


# ─── DELETE /saved-cards/{card_id} ───────────
@router.delete("/saved-cards/{card_id}", response_model=DeleteCardResponse, summary="Delete Saved Card")
async def remove_card(
    card_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    return await delete_saved_card(db, card_id, user_id)


# ─── GET /refunds ────────────────────────────
@router.get("/refunds", response_model=RefundsListResponse, summary="Get Refunds")
async def refunds_list(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    return await get_refunds(db, user_id)


# ─── POST /refund/request ────────────────────
@router.post("/refund/request", response_model=RefundResponse, summary="Request Refund")
async def refund_request(
    data: RefundRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    data.user_id = user_id
    return await request_refund(db, data)


# ─── GET /refund/{refund_id} ─────────────────
@router.get("/refund/{refund_id}", response_model=RefundResponse, summary="Get Refund")
async def refund_detail(
    refund_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    return await get_refund(db, refund_id)


# ─── POST /pay-later/check ───────────────────
@router.post("/pay-later/check", response_model=PayLaterCheckResponse, summary="Check Pay Later Eligibility")
async def pay_later_check(
    data: PayLaterCheckRequest,
    user_id: UUID = Depends(get_current_user_id),
):
    data.user_id = user_id
    return check_pay_later(data)


# ─── POST /pay-later/apply ───────────────────
@router.post("/pay-later/apply", response_model=PayLaterApplyResponse, summary="Apply Pay Later")
async def pay_later_apply(
    data: PayLaterApplyRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    data.user_id = user_id
    return await apply_pay_later(db, data)


# ─── POST /webhook/razorpay (no auth) ────────
@router.post("/webhook/razorpay", summary="Razorpay Webhook")
async def razorpay_webhook(
    payload: WebhookPayload,
    db: AsyncSession = Depends(get_db),
):
    return await handle_webhook(db, payload.dict())


# ─── GET /{transaction_id} ───────────────────
@router.get("/{transaction_id}", response_model=TransactionOut, summary="Get Transaction")
async def transaction_detail(
    transaction_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    txn = await get_transaction(db, transaction_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    return txn