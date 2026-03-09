"""
services/wallet_service.py
All Wallet business logic:
balance, topup (Razorpay), verify payment, transactions, withdrawal.
"""

import hmac
import hashlib
from decimal import Decimal
from datetime import datetime
from typing import Optional

import razorpay
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.models.wallet import Wallet, WalletTransaction, WithdrawalRequest
from src.models.user import User
from src.schemas.wallet import (
    TopupInitiateRequest, TopupVerifyRequest, WithdrawRequest
)
from src.core.config import settings


# ── Razorpay Client ───────────────────────────────────────────
def get_razorpay_client():
    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

async def get_or_create_wallet(user_id: str, db: AsyncSession) -> Wallet:
    """
    Get wallet for user. If wallet doesn't exist yet, create one.
    Every user gets a wallet automatically.
    """
    result = await db.execute(
        select(Wallet).where(Wallet.user_id == user_id)
    )
    wallet = result.scalar_one_or_none()

    if not wallet:
        wallet = Wallet(user_id=user_id, balance=Decimal("0.00"), status="active")
        db.add(wallet)
        await db.commit()
        await db.refresh(wallet)

    return wallet


async def record_transaction(
    wallet: Wallet,
    txn_type: str,
    category: str,
    amount: Decimal,
    description: str,
    reference_id: Optional[str] = None,
    status: str = "success",
    db: AsyncSession = None
) -> WalletTransaction:
    """
    Create a transaction record and update wallet balance.
    txn_type: 'credit' or 'debit'
    """
    if txn_type == "credit":
        wallet.balance += amount
    elif txn_type == "debit":
        if wallet.balance < amount:
            raise ValueError("Insufficient wallet balance")
        wallet.balance -= amount

    txn = WalletTransaction(
        wallet_id     = wallet.id,
        type          = txn_type,
        category      = category,
        amount        = amount,
        balance_after = wallet.balance,
        description   = description,
        reference_id  = reference_id,
        status        = status,
    )
    db.add(txn)
    await db.commit()
    await db.refresh(wallet)
    await db.refresh(txn)
    return txn


# ═══════════════════════════════════════════════════════════════
# 1. GET BALANCE
# GET /wallet/balance
# ═══════════════════════════════════════════════════════════════

async def get_balance(user: User, db: AsyncSession) -> Wallet:
    """Get wallet balance for the current user."""
    wallet = await get_or_create_wallet(str(user.id), db)
    return wallet


# ═══════════════════════════════════════════════════════════════
# 2. INITIATE TOPUP
# POST /wallet/topup
# Creates Razorpay order → returns order details to frontend
# ═══════════════════════════════════════════════════════════════

async def initiate_topup(
    data: TopupInitiateRequest,
    user: User,
    db: AsyncSession
) -> dict:
    """
    Create a Razorpay order for wallet topup.
    Frontend uses order_id + key_id to open Razorpay payment modal.
    """
    wallet = await get_or_create_wallet(str(user.id), db)

    if wallet.status != "active":
        raise ValueError("Your wallet is frozen. Contact support.")

    # Amount in paise (Razorpay uses smallest currency unit)
    amount_paise = int(data.amount * 100)

    client = get_razorpay_client()
    order = client.order.create({
        "amount":   amount_paise,
        "currency": "INR",
        "notes": {
            "user_id":   str(user.id),
            "wallet_id": str(wallet.id),
            "purpose":   "wallet_topup"
        }
    })

    return {
        "order_id": order["id"],
        "amount":   amount_paise,
        "currency": "INR",
        "key_id":   settings.RAZORPAY_KEY_ID,
    }


# ═══════════════════════════════════════════════════════════════
# 3. VERIFY TOPUP PAYMENT
# POST /wallet/topup/verify
# Verifies Razorpay signature → credits wallet
# ═══════════════════════════════════════════════════════════════

async def verify_topup(
    data: TopupVerifyRequest,
    user: User,
    db: AsyncSession
) -> dict:
    """
    Verify Razorpay payment signature.
    If valid → credit wallet balance.
    If invalid → reject (possible tampering).
    """
    # ── Step 1: Verify HMAC-SHA256 Signature ──────────────────
    expected_signature = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        f"{data.razorpay_order_id}|{data.razorpay_payment_id}".encode(),
        hashlib.sha256
    ).hexdigest()

    if expected_signature != data.razorpay_signature:
        raise ValueError("Invalid payment signature. Payment verification failed.")

    # ── Step 2: Fetch payment details from Razorpay ───────────
    client = get_razorpay_client()
    payment = client.payment.fetch(data.razorpay_payment_id)

    if payment["status"] != "captured":
        raise ValueError(f"Payment not captured. Status: {payment['status']}")

    # ── Step 3: Credit wallet ─────────────────────────────────
    amount_inr = Decimal(str(payment["amount"] / 100))   # convert paise to INR

    wallet = await get_or_create_wallet(str(user.id), db)

    txn = await record_transaction(
        wallet      = wallet,
        txn_type    = "credit",
        category    = "topup",
        amount      = amount_inr,
        description = f"Wallet topup via Razorpay",
        reference_id = data.razorpay_payment_id,
        db          = db,
    )

    return {
        "message":         "Wallet topped up successfully",
        "amount_credited": amount_inr,
        "new_balance":     wallet.balance,
        "transaction_id":  str(txn.id),
    }


# ═══════════════════════════════════════════════════════════════
# 4. LIST TRANSACTIONS
# GET /wallet/transactions
# ═══════════════════════════════════════════════════════════════

async def list_transactions(
    user: User,
    db: AsyncSession,
    page: int = 1,
    per_page: int = 20,
    txn_type: Optional[str] = None,    # credit / debit
    category: Optional[str] = None,    # topup / booking_payment / etc
) -> dict:
    """List all wallet transactions for the user with pagination."""
    wallet = await get_or_create_wallet(str(user.id), db)

    query = select(WalletTransaction).where(
        WalletTransaction.wallet_id == wallet.id
    )

    # Optional filters
    if txn_type:
        query = query.where(WalletTransaction.type == txn_type)
    if category:
        query = query.where(WalletTransaction.category == category)

    # Total count
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar()

    # Paginate — newest first
    query = query.order_by(
        WalletTransaction.created_at.desc()
    ).offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    transactions = result.scalars().all()

    return {
        "transactions": transactions,
        "total":        total,
        "page":         page,
        "per_page":     per_page,
    }


# ═══════════════════════════════════════════════════════════════
# 5. GET TRANSACTION DETAILS
# GET /wallet/transactions/{id}
# ═══════════════════════════════════════════════════════════════

async def get_transaction(
    txn_id: str,
    user: User,
    db: AsyncSession
) -> WalletTransaction:
    """Get a single transaction by ID — must belong to current user."""
    wallet = await get_or_create_wallet(str(user.id), db)

    result = await db.execute(
        select(WalletTransaction).where(
            WalletTransaction.id == txn_id,
            WalletTransaction.wallet_id == wallet.id  # ownership check
        )
    )
    txn = result.scalar_one_or_none()
    if not txn:
        raise ValueError("Transaction not found")
    return txn


# ═══════════════════════════════════════════════════════════════
# 6. REQUEST WITHDRAWAL
# POST /wallet/withdraw
# ═══════════════════════════════════════════════════════════════

async def request_withdrawal(
    data: WithdrawRequest,
    user: User,
    db: AsyncSession
) -> WithdrawalRequest:
    """
    Request a withdrawal to bank account.
    - Checks sufficient balance
    - Deducts from wallet immediately
    - Creates withdrawal request (processed by admin/cron)
    """
    wallet = await get_or_create_wallet(str(user.id), db)

    if wallet.status != "active":
        raise ValueError("Your wallet is frozen. Contact support.")

    if wallet.balance < data.amount:
        raise ValueError(
            f"Insufficient balance. Available: ₹{wallet.balance}"
        )

    # Deduct balance immediately (held until processed)
    await record_transaction(
        wallet      = wallet,
        txn_type    = "debit",
        category    = "withdrawal",
        amount      = data.amount,
        description = f"Withdrawal to bank account ending {str(data.bank_account_number)[-4:]}",
        db          = db,
    )

    # Create withdrawal request
    withdrawal = WithdrawalRequest(
        wallet_id           = wallet.id,
        amount              = data.amount,
        bank_account_number = data.bank_account_number,
        bank_ifsc           = data.bank_ifsc,
        bank_name           = data.bank_name,
        account_holder_name = data.account_holder_name,
        status              = "pending",
    )
    db.add(withdrawal)
    await db.commit()
    await db.refresh(withdrawal)

    return withdrawal


# ═══════════════════════════════════════════════════════════════
# 7. LIST WITHDRAWAL REQUESTS
# GET /wallet/withdraw/requests
# ═══════════════════════════════════════════════════════════════

async def list_withdrawal_requests(
    user: User,
    db: AsyncSession,
    page: int = 1,
    per_page: int = 10,
) -> dict:
    """List all withdrawal requests for the current user."""
    wallet = await get_or_create_wallet(str(user.id), db)

    query = select(WithdrawalRequest).where(
        WithdrawalRequest.wallet_id == wallet.id
    )

    # Total count
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar()

    # Paginate — newest first
    query = query.order_by(
        WithdrawalRequest.created_at.desc()
    ).offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    requests = result.scalars().all()

    return {
        "requests": requests,
        "total":    total,
    }
