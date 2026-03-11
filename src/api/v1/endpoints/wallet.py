
"""
api/v1/endpoints/wallet.py
All 7 Wallet API endpoints.

Routes:
  GET  /wallet/balance               → Get wallet balance
  POST /wallet/topup                 → Initiate Razorpay topup
  POST /wallet/topup/verify          → Verify payment + credit wallet
  GET  /wallet/transactions          → List transactions (paginated)
  GET  /wallet/transactions/{id}     → Transaction details
  POST /wallet/withdraw              → Request withdrawal
  GET  /wallet/withdraw/requests     → List withdrawal requests
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from src.core.database import get_db
from src.api.deps.auth import get_current_user, get_verified_user
from src.models.user import User
from src.schemas.wallet import (
    TopupInitiateRequest, TopupVerifyRequest, WithdrawRequest,
    WalletBalanceResponse, TopupInitiateResponse,
    TransactionResponse, TransactionListResponse,
    WithdrawalResponse, WithdrawalListResponse,
)
from src.common.responses import APIResponse
from src.services import wallet_service

router = APIRouter(prefix="/wallet", tags=["Wallet"])


# ── 1. GET BALANCE ────────────────────────────────────────────
@router.get(
    "/balance",
    response_model=APIResponse,
    summary="Get wallet balance"
)
async def get_balance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current wallet balance for the logged-in user.
    Wallet is auto-created if it doesn't exist yet.
    """
    wallet = await wallet_service.get_balance(current_user, db)
    return APIResponse.success(
        message="Wallet balance fetched",
        data={
            "wallet_id": str(wallet.id),
            "balance":   str(wallet.balance),
            "status":    wallet.status,
            "currency":  "INR",
        }
    )


# ── 2. INITIATE TOPUP ─────────────────────────────────────────
@router.post(
    "/topup",
    response_model=APIResponse,
    summary="Initiate wallet topup via Razorpay"
)
async def initiate_topup(
    data: TopupInitiateRequest,
    current_user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a Razorpay order to top up the wallet.

    **Flow:**
    1. Call this endpoint → get `order_id` + `key_id`
    2. Open Razorpay payment modal on frontend using these values
    3. User completes payment
    4. Call `/wallet/topup/verify` with the payment details

    **Minimum:** ₹10 | **Maximum:** ₹1,00,000
    """
    try:
        result = await wallet_service.initiate_topup(data, current_user, db)
        return APIResponse.success(
            message="Razorpay order created. Complete payment to top up wallet.",
            data=result
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── 3. VERIFY TOPUP PAYMENT ───────────────────────────────────
@router.post(
    "/topup/verify",
    response_model=APIResponse,
    summary="Verify Razorpay payment and credit wallet"
)
async def verify_topup(
    data: TopupVerifyRequest,
    current_user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Verify Razorpay payment signature and credit wallet balance.

    **Send these values from Razorpay callback:**
    - `razorpay_order_id`
    - `razorpay_payment_id`
    - `razorpay_signature`

    If signature is valid → wallet is credited immediately.
    If signature is invalid → request is rejected (tampering detected).
    """
    try:
        result = await wallet_service.verify_topup(data, current_user, db)
        return APIResponse.success(
            message=result["message"],
            data={
                "amount_credited": str(result["amount_credited"]),
                "new_balance":     str(result["new_balance"]),
                "transaction_id":  result["transaction_id"],
                "currency":        "INR",
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── 4. LIST TRANSACTIONS ──────────────────────────────────────
@router.get(
    "/transactions",
    response_model=APIResponse,
    summary="List wallet transactions"
)
async def list_transactions(
    page:     int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    type:     Optional[str] = Query(default=None, description="credit or debit"),
    category: Optional[str] = Query(default=None, description="topup / booking_payment / refund / withdrawal"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all wallet transactions with pagination.

    **Filters:**
    - `type`: `credit` or `debit`
    - `category`: `topup`, `booking_payment`, `booking_refund`, `withdrawal`, `cashback`

    Returns newest transactions first.
    """
    result = await wallet_service.list_transactions(
        user     = current_user,
        db       = db,
        page     = page,
        per_page = per_page,
        txn_type = type,
        category = category,
    )
    return APIResponse.success(
        message="Transactions fetched",
        data={
            "transactions": [
                {
                    "id":            str(t.id),
                    "type":          t.type,
                    "category":      t.category,
                    "amount":        str(t.amount),
                    "balance_after": str(t.balance_after),
                    "description":   t.description,
                    "reference_id":  t.reference_id,
                    "status":        t.status,
                    "created_at":    t.created_at.isoformat(),
                }
                for t in result["transactions"]
            ],
            "total":    result["total"],
            "page":     result["page"],
            "per_page": result["per_page"],
        }
    )


# ── 5. TRANSACTION DETAILS ────────────────────────────────────
@router.get(
    "/transactions/{txn_id}",
    response_model=APIResponse,
    summary="Get transaction details"
)
async def get_transaction(
    txn_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get details of a single wallet transaction by ID."""
    try:
        txn = await wallet_service.get_transaction(txn_id, current_user, db)
        return APIResponse.success(
            message="Transaction details fetched",
            data={
                "id":            str(txn.id),
                "type":          txn.type,
                "category":      txn.category,
                "amount":        str(txn.amount),
                "balance_after": str(txn.balance_after),
                "description":   txn.description,
                "reference_id":  txn.reference_id,
                "status":        txn.status,
                "created_at":    txn.created_at.isoformat(),
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ── 6. REQUEST WITHDRAWAL ─────────────────────────────────────
@router.post(
    "/withdraw",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Request withdrawal to bank account"
)
async def request_withdrawal(
    data: WithdrawRequest,
    current_user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Request a withdrawal from wallet to bank account.

    - Minimum withdrawal: ₹100
    - Balance is deducted immediately and held
    - Withdrawal is processed within 2-3 business days
    - Status can be tracked via `/wallet/withdraw/requests`
    """
    try:
        withdrawal = await wallet_service.request_withdrawal(data, current_user, db)
        return APIResponse.success(
            message="Withdrawal request submitted. Will be processed in 2-3 business days.",
            data={
                "id":                  str(withdrawal.id),
                "amount":              str(withdrawal.amount),
                "bank_account_number": withdrawal.bank_account_number[-4:].rjust(len(withdrawal.bank_account_number), "*"),
                "bank_ifsc":           withdrawal.bank_ifsc,
                "status":              withdrawal.status,
                "created_at":          withdrawal.created_at.isoformat(),
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── 7. LIST WITHDRAWAL REQUESTS ───────────────────────────────
@router.get(
    "/withdraw/requests",
    response_model=APIResponse,
    summary="List withdrawal requests"
)
async def list_withdrawal_requests(
    page:     int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all withdrawal requests for the current user.
    Shows status: pending / processing / completed / rejected.
    """
    result = await wallet_service.list_withdrawal_requests(
        user     = current_user,
        db       = db,
        page     = page,
        per_page = per_page,
    )
    return APIResponse.success(
        message="Withdrawal requests fetched",
        data={
            "requests": [
                {
                    "id":                  str(r.id),
                    "amount":              str(r.amount),
                    "bank_account_number": r.bank_account_number[-4:].rjust(len(r.bank_account_number), "*"),
                    "bank_ifsc":           r.bank_ifsc,
                    "bank_name":           r.bank_name,
                    "status":              r.status,
                    "rejection_reason":    r.rejection_reason,
                    "created_at":          r.created_at.isoformat(),
                    "processed_at":        r.processed_at.isoformat() if r.processed_at else None,
                }
                for r in result["requests"]
            ],
            "total": result["total"],
        }
    )
