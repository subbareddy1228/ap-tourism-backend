"""
api/v1/endpoints/payments.py
Payment module — fixed for LEV146 integration.
Changes:
  - from src.database → from src.core.database
  - Uses get_current_user from src.api.deps.auth (LEV146 pattern)
  - Uses APIResponse wrapper
  - prefix /payments (not /payment) — consistent with LEV146 naming
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.api.deps.auth import get_current_user
from src.models.user import User
from src.common.responses import APIResponse
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

router = APIRouter(prefix="/payments", tags=["Payments"])


# ─── GET /methods (no auth needed) ───────────
@router.get(
    "/methods",
    response_model=PaymentMethodsResponse,
    summary="Get payment methods"
)
async def payment_methods():
    """
    List all available payment methods:
    UPI, CARD, NET_BANKING, WALLET, EMI, PAY_LATER.
    """

    methods = await get_payment_methods()

    return methods


# ─── POST /initiate ───────────────────────────
@router.post("/initiate", response_model=InitiatePaymentResponse, status_code=201, summary="Initiate payment")
async def initiate(
    data: InitiatePaymentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create Razorpay order and return order_id for frontend."""
    data.user_id = current_user.id
    return await initiate_payment(db, data)


# ─── POST /verify ─────────────────────────────
@router.post("/verify", response_model=VerifyPaymentResponse, summary="Verify payment signature")
async def verify(
    data: VerifyPaymentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify Razorpay HMAC signature and mark transaction SUCCESS or FAILED."""
    return await verify_payment(db, data)


# ─── GET /history ─────────────────────────────
@router.get("/history", response_model=PaymentHistoryResponse, summary="Payment history")
async def history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """All transactions for the current user."""
    return await get_payment_history(db, current_user.id)


# ─── POST /validate-upi ───────────────────────
@router.post("/validate-upi", response_model=ValidateUPIResponse, summary="Validate UPI ID")
async def validate_upi_id(
    data: ValidateUPIRequest,
    current_user: User = Depends(get_current_user),
):
    """Validate format of a UPI ID."""
    return validate_upi(data)


# ─── GET /saved-cards ─────────────────────────
@router.get("/saved-cards", response_model=SavedCardsResponse, summary="Get saved cards")
async def saved_cards(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_saved_cards(db, current_user.id)


# ─── POST /saved-cards ────────────────────────
@router.post("/saved-cards", response_model=SaveCardResponse, status_code=201, summary="Save card")
async def add_card(
    data: SaveCardRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data.user_id = current_user.id
    return await save_card(db, data)


# ─── DELETE /saved-cards/{card_id} ───────────
@router.delete("/saved-cards/{card_id}", response_model=DeleteCardResponse, summary="Delete saved card")
async def remove_card(
    card_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await delete_saved_card(db, card_id, current_user.id)


# ─── GET /refunds ─────────────────────────────
@router.get("/refunds", response_model=RefundsListResponse, summary="List refunds")
async def refunds_list(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_refunds(db, current_user.id)


# ─── POST /refund/request ─────────────────────
@router.post("/refund/request", response_model=RefundResponse, status_code=201, summary="Request refund")
async def refund_request(
    data: RefundRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data.user_id = current_user.id
    return await request_refund(db, data)


# ─── GET /refund/{refund_id} ──────────────────
@router.get("/refund/{refund_id}", response_model=RefundResponse, summary="Get refund detail")
async def refund_detail(
    refund_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_refund(db, refund_id)


# ─── POST /pay-later/check ────────────────────
@router.post("/pay-later/check", response_model=PayLaterCheckResponse, summary="Check Pay Later eligibility")
async def pay_later_check(
    data: PayLaterCheckRequest,
    current_user: User = Depends(get_current_user),
):
    data.user_id = current_user.id
    return check_pay_later(data)


# ─── POST /pay-later/apply ────────────────────
@router.post("/pay-later/apply", response_model=PayLaterApplyResponse, status_code=201, summary="Apply Pay Later")
async def pay_later_apply(
    data: PayLaterApplyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data.user_id = current_user.id
    return await apply_pay_later(db, data)


from src.integrations.razorpay import verify_webhook_signature as rzp_verify_webhook

# ─── POST /webhook/razorpay (no auth) ─────────
@router.post("/webhook/razorpay", summary="Razorpay webhook")
async def razorpay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Called by Razorpay on payment events.
    Verifies X-Razorpay-Signature before processing.
    """
    raw_body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")

    if not rzp_verify_webhook(raw_body, signature):
        raise HTTPException(status_code=400, detail="Invalid webhook signature.")

    import json
    payload = json.loads(raw_body)
    return await handle_webhook(db, payload)


# ─── GET /{transaction_id} ────────────────────
@router.get("/{transaction_id}", response_model=TransactionOut, summary="Get transaction detail")
async def transaction_detail(
    transaction_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    txn = await get_transaction(db, transaction_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    return txn