# """
# api/v1/endpoints/wallet.py
# All 7 Wallet API endpoints.

# Routes:
#   GET  /wallet/balance               → Get wallet balance
#   POST /wallet/topup                 → Initiate Razorpay topup
#   POST /wallet/topup/verify          → Verify payment + credit wallet
#   GET  /wallet/transactions          → List transactions (paginated)
#   GET  /wallet/transactions/{id}     → Transaction details
#   POST /wallet/withdraw              → Request withdrawal
#   GET  /wallet/withdraw/requests     → List withdrawal requests
# """

# from fastapi import APIRouter, Depends, HTTPException, status, Query
# from sqlalchemy.ext.asyncio import AsyncSession
# from typing import Optional

# from src.core.database import get_db
# from src.api.deps.auth import get_current_user, get_verified_user
# from src.models.user import User
# from src.schemas.wallet import (
#     TopupInitiateRequest, TopupVerifyRequest, WithdrawRequest,
#     WalletBalanceResponse, TopupInitiateResponse,
#     TransactionResponse, TransactionListResponse,
#     WithdrawalResponse, WithdrawalListResponse,
# )
# from src.common.responses import APIResponse
# from src.services import wallet_service

# router = APIRouter(prefix="/wallet", tags=["Wallet"])


# # ── 1. GET BALANCE ────────────────────────────────────────────
# @router.get(
#     "/balance",
#     response_model=APIResponse,
#     summary="Get wallet balance"
# )
# async def get_balance(
#     current_user: User = Depends(get_current_user),
#     db: AsyncSession = Depends(get_db)
# ):
#     """
#     Get current wallet balance for the logged-in user.
#     Wallet is auto-created if it doesn't exist yet.
#     """
#     wallet = await wallet_service.get_balance(current_user, db)
#     return APIResponse.success(
#         message="Wallet balance fetched",
#         data={
#             "wallet_id": str(wallet.id),
#             "balance":   str(wallet.balance),
#             "status":    wallet.status,
#             "currency":  "INR",
#         }
#     )


# # ── 2. INITIATE TOPUP ─────────────────────────────────────────
# @router.post(
#     "/topup",
#     response_model=APIResponse,
#     summary="Initiate wallet topup via Razorpay"
# )
# async def initiate_topup(
#     data: TopupInitiateRequest,
#     current_user: User = Depends(get_verified_user),
#     db: AsyncSession = Depends(get_db)
# ):
#     """
#     Create a Razorpay order to top up the wallet.

#     **Flow:**
#     1. Call this endpoint → get `order_id` + `key_id`
#     2. Open Razorpay payment modal on frontend using these values
#     3. User completes payment
#     4. Call `/wallet/topup/verify` with the payment details

#     **Minimum:** ₹10 | **Maximum:** ₹1,00,000
#     """
#     try:
#         result = await wallet_service.initiate_topup(data, current_user, db)
#         return APIResponse.success(
#             message="Razorpay order created. Complete payment to top up wallet.",
#             data=result
#         )
#     except ValueError as e:
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# # ── 3. VERIFY TOPUP PAYMENT ───────────────────────────────────
# @router.post(
#     "/topup/verify",
#     response_model=APIResponse,
#     summary="Verify Razorpay payment and credit wallet"
# )
# async def verify_topup(
#     data: TopupVerifyRequest,
#     current_user: User = Depends(get_verified_user),
#     db: AsyncSession = Depends(get_db)
# ):
#     """
#     Verify Razorpay payment signature and credit wallet balance.

#     **Send these values from Razorpay callback:**
#     - `razorpay_order_id`
#     - `razorpay_payment_id`
#     - `razorpay_signature`

#     If signature is valid → wallet is credited immediately.
#     If signature is invalid → request is rejected (tampering detected).
#     """
#     try:
#         result = await wallet_service.verify_topup(data, current_user, db)
#         return APIResponse.success(
#             message=result["message"],
#             data={
#                 "amount_credited": str(result["amount_credited"]),
#                 "new_balance":     str(result["new_balance"]),
#                 "transaction_id":  result["transaction_id"],
#                 "currency":        "INR",
#             }
#         )
#     except ValueError as e:
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# # ── 4. LIST TRANSACTIONS ──────────────────────────────────────
# @router.get(
#     "/transactions",
#     response_model=APIResponse,
#     summary="List wallet transactions"
# )
# async def list_transactions(
#     page:     int = Query(default=1, ge=1),
#     per_page: int = Query(default=20, ge=1, le=100),
#     type:     Optional[str] = Query(default=None, description="credit or debit"),
#     category: Optional[str] = Query(default=None, description="topup / booking_payment / refund / withdrawal"),
#     current_user: User = Depends(get_current_user),
#     db: AsyncSession = Depends(get_db)
# ):
#     """
#     List all wallet transactions with pagination.

#     **Filters:**
#     - `type`: `credit` or `debit`
#     - `category`: `topup`, `booking_payment`, `booking_refund`, `withdrawal`, `cashback`

#     Returns newest transactions first.
#     """
#     result = await wallet_service.list_transactions(
#         user     = current_user,
#         db       = db,
#         page     = page,
#         per_page = per_page,
#         txn_type = type,
#         category = category,
#     )
#     return APIResponse.success(
#         message="Transactions fetched",
#         data={
#             "transactions": [
#                 {
#                     "id":            str(t.id),
#                     "type":          t.type,
#                     "category":      t.category,
#                     "amount":        str(t.amount),
#                     "balance_after": str(t.balance_after),
#                     "description":   t.description,
#                     "reference_id":  t.reference_id,
#                     "status":        t.status,
#                     "created_at":    t.created_at.isoformat(),
#                 }
#                 for t in result["transactions"]
#             ],
#             "total":    result["total"],
#             "page":     result["page"],
#             "per_page": result["per_page"],
#         }
#     )


# # ── 5. TRANSACTION DETAILS ────────────────────────────────────
# @router.get(
#     "/transactions/{txn_id}",
#     response_model=APIResponse,
#     summary="Get transaction details"
# )
# async def get_transaction(
#     txn_id: str,
#     current_user: User = Depends(get_current_user),
#     db: AsyncSession = Depends(get_db)
# ):
#     """Get details of a single wallet transaction by ID."""
#     try:
#         txn = await wallet_service.get_transaction(txn_id, current_user, db)
#         return APIResponse.success(
#             message="Transaction details fetched",
#             data={
#                 "id":            str(txn.id),
#                 "type":          txn.type,
#                 "category":      txn.category,
#                 "amount":        str(txn.amount),
#                 "balance_after": str(txn.balance_after),
#                 "description":   txn.description,
#                 "reference_id":  txn.reference_id,
#                 "status":        txn.status,
#                 "created_at":    txn.created_at.isoformat(),
#             }
#         )
#     except ValueError as e:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# # ── 6. REQUEST WITHDRAWAL ─────────────────────────────────────
# @router.post(
#     "/withdraw",
#     response_model=APIResponse,
#     status_code=status.HTTP_201_CREATED,
#     summary="Request withdrawal to bank account"
# )
# async def request_withdrawal(
#     data: WithdrawRequest,
#     current_user: User = Depends(get_verified_user),
#     db: AsyncSession = Depends(get_db)
# ):
#     """
#     Request a withdrawal from wallet to bank account.

#     - Minimum withdrawal: ₹100
#     - Balance is deducted immediately and held
#     - Withdrawal is processed within 2-3 business days
#     - Status can be tracked via `/wallet/withdraw/requests`
#     """
#     try:
#         withdrawal = await wallet_service.request_withdrawal(data, current_user, db)
#         return APIResponse.success(
#             message="Withdrawal request submitted. Will be processed in 2-3 business days.",
#             data={
#                 "id":                  str(withdrawal.id),
#                 "amount":              str(withdrawal.amount),
#                 "bank_account_number": withdrawal.bank_account_number[-4:].rjust(len(withdrawal.bank_account_number), "*"),
#                 "bank_ifsc":           withdrawal.bank_ifsc,
#                 "status":              withdrawal.status,
#                 "created_at":          withdrawal.created_at.isoformat(),
#             }
#         )
#     except ValueError as e:
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# # ── 7. LIST WITHDRAWAL REQUESTS ───────────────────────────────
# @router.get(
#     "/withdraw/requests",
#     response_model=APIResponse,
#     summary="List withdrawal requests"
# )
# async def list_withdrawal_requests(
#     page:     int = Query(default=1, ge=1),
#     per_page: int = Query(default=10, ge=1, le=50),
#     current_user: User = Depends(get_current_user),
#     db: AsyncSession = Depends(get_db)
# ):
#     """
#     List all withdrawal requests for the current user.
#     Shows status: pending / processing / completed / rejected.
#     """
#     result = await wallet_service.list_withdrawal_requests(
#         user     = current_user,
#         db       = db,
#         page     = page,
#         per_page = per_page,
#     )
#     return APIResponse.success(
#         message="Withdrawal requests fetched",
#         data={
#             "requests": [
#                 {
#                     "id":                  str(r.id),
#                     "amount":              str(r.amount),
#                     "bank_account_number": r.bank_account_number[-4:].rjust(len(r.bank_account_number), "*"),
#                     "bank_ifsc":           r.bank_ifsc,
#                     "bank_name":           r.bank_name,
#                     "status":              r.status,
#                     "rejection_reason":    r.rejection_reason,
#                     "created_at":          r.created_at.isoformat(),
#                     "processed_at":        r.processed_at.isoformat() if r.processed_at else None,
#                 }
#                 for r in result["requests"]
#             ],
#             "total": result["total"],
#         }
#     )



# from fastapi import APIRouter

# router = APIRouter(prefix="/wallet", tags=["Wallet"])

# @router.get("/health")
# async def wallet_health():
#     return {"status": "wallet ok"}







"""
src/api/v1/endpoints/wallet.py
Module 3 — Wallet APIs /api/v1/wallet
Author: LEV146
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid
import enum

from src.core.database import get_db 

from src.models.user import User
from src.models.wallet import WalletTransaction, WithdrawalRequest, TransactionType, WithdrawalStatus
from src.api.deps.auth import get_current_user, get_verified_user

router = APIRouter(prefix="/wallet", tags=["Wallet"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class TopupRequest(BaseModel):
    amount: float

class TopupVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

class WithdrawRequest(BaseModel):
    amount: float
    bank_account_number: str
    ifsc_code: str
    account_holder_name: str


# ─── Balance ──────────────────────────────────────────────────────────────────

@router.get("/balance")
def get_balance(current_user: User = Depends(get_current_user)):
    """GET /balance — Return current wallet balance."""
    return {
        "success": True,
        "data": {
            "balance": current_user.wallet_balance,
            "currency": "INR",
        }
    }


# ─── Transactions ─────────────────────────────────────────────────────────────

@router.get("/transactions")
def get_transactions(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """GET /transactions — Paginated list of all wallet transactions."""
    offset = (page - 1) * limit
    total = db.query(WalletTransaction).filter(WalletTransaction.user_id == current_user.id).count()
    transactions = (
        db.query(WalletTransaction)
        .filter(WalletTransaction.user_id == current_user.id)
        .order_by(WalletTransaction.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "success": True,
        "data": {
            "total": total,
            "page": page,
            "limit": limit,
            "transactions": [
                {
                    "id": str(t.id),
                    "type": t.type,
                    "amount": t.amount,
                    "reference": t.reference,
                    "description": t.description,
                    "created_at": t.created_at,
                }
                for t in transactions
            ],
        },
    }


@router.get("/transactions/{transaction_id}")
def get_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """GET /transactions/{id} — Single transaction detail."""
    txn = db.query(WalletTransaction).filter(
        and_(
            WalletTransaction.id == transaction_id,
            WalletTransaction.user_id == current_user.id,
        )
    ).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {
        "success": True,
        "data": {
            "id": str(txn.id),
            "type": txn.type,
            "amount": txn.amount,
            "reference": txn.reference,
            "description": txn.description,
            "created_at": txn.created_at,
        },
    }


# ─── Top Up ───────────────────────────────────────────────────────────────────

@router.post("/topup")
def initiate_topup(
    body: TopupRequest,
    current_user: User = Depends(get_verified_user),
):
    """POST /topup — Initiate wallet topup via Razorpay."""
    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than 0")

    # TODO: Create Razorpay order using razorpay client
    # import razorpay
    # client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    # order = client.order.create({"amount": int(body.amount * 100), "currency": "INR"})

    fake_order_id = f"order_{uuid.uuid4().hex[:16]}"
    return {
        "success": True,
        "data": {
            "razorpay_order_id": fake_order_id,
            "amount": body.amount,
            "currency": "INR",
        },
    }


@router.post("/topup/verify")
def verify_topup(
    body: TopupVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_verified_user),
):
    """POST /topup/verify — Verify Razorpay payment and credit wallet."""
    # TODO: Verify razorpay_signature using HMAC
    # For now we trust the payment

    # Extract amount from order (in real code, fetch from Razorpay)
    amount = 100.0  # placeholder — fetch from Razorpay order

    # Credit wallet balance
    current_user.wallet_balance += amount

    # Log transaction
    txn = WalletTransaction(
        user_id=current_user.id,
        type=TransactionType.CREDIT,
        amount=amount,
        reference=body.razorpay_payment_id,
        description="Wallet topup via Razorpay",
    )
    db.add(txn)
    db.commit()

    return {
        "success": True,
        "message": "Wallet credited successfully",
        "new_balance": current_user.wallet_balance,
    }


# ─── Withdraw ─────────────────────────────────────────────────────────────────

@router.post("/withdraw")
def request_withdrawal(
    body: WithdrawRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_verified_user),
):
    """POST /withdraw — Request withdrawal to bank account."""
    if body.amount < 500:
        raise HTTPException(status_code=400, detail="Minimum withdrawal amount is ₹500")
    if current_user.wallet_balance < body.amount:
        raise HTTPException(status_code=400, detail="Insufficient wallet balance")

    # Deduct balance and create withdrawal request
    current_user.wallet_balance -= body.amount

    withdrawal = WithdrawalRequest(
        user_id=current_user.id,
        amount=body.amount,
        bank_account_number=body.bank_account_number,
        ifsc_code=body.ifsc_code,
        account_holder_name=body.account_holder_name,
        status=WithdrawalStatus.PENDING,
    )
    db.add(withdrawal)

    # Log debit transaction
    txn = WalletTransaction(
        user_id=current_user.id,
        type=TransactionType.DEBIT,
        amount=body.amount,
        reference=str(withdrawal.id),
        description="Withdrawal request",
    )
    db.add(txn)
    db.commit()

    return {
        "success": True,
        "message": "Withdrawal request submitted",
        "data": {
            "id": str(withdrawal.id),
            "amount": body.amount,
            "status": "PENDING",
        },
    }


@router.get("/withdraw/requests")
def get_withdrawal_requests(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """GET /withdraw/requests — List withdrawal requests."""
    query = db.query(WithdrawalRequest).filter(WithdrawalRequest.user_id == current_user.id)
    if status_filter:
        query = query.filter(WithdrawalRequest.status == status_filter)
    requests = query.order_by(WithdrawalRequest.created_at.desc()).all()
    return {
        "success": True,
        "data": [
            {
                "id": str(r.id),
                "amount": r.amount,
                "status": r.status,
                "bank_account_number": r.bank_account_number[-4:].rjust(len(r.bank_account_number), "*"),
                "created_at": r.created_at,
            }
            for r in requests
        ],
    }
