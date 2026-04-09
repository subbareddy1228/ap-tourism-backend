"""
repositories/transaction_repo.py
DB access for Transaction, SavedCard, and Refund models.
Used by payment_service.py.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update

from src.models.transaction import Transaction, SavedCard, Refund


# ── Transactions ──────────────────────────────────────────────────────────────

async def create_transaction(db: AsyncSession, data: dict) -> Transaction:
    """
    INSERT a new transaction row.
    Called by payment_service.initiate_payment and apply_pay_later
    instead of constructing Transaction inline.
    """
    now = datetime.utcnow()
    txn = Transaction(
        booking_id        = data["booking_id"],
        user_id           = data["user_id"],
        amount            = data["amount"],
        currency          = data.get("currency", "INR"),
        status            = data.get("status", "INITIATED"),
        payment_method    = data.get("payment_method"),
        razorpay_order_id = data.get("razorpay_order_id"),
        payment_metadata  = data.get("payment_metadata"),
        initiated_at      = data.get("initiated_at", now),
        created_at        = now,
        updated_at        = now,
    )
    db.add(txn)
    await db.commit()
    await db.refresh(txn)
    return txn


async def update_transaction_status(
    db: AsyncSession,
    txn_id: UUID,
    status: str,
    *,
    razorpay_payment_id: Optional[str] = None,
    razorpay_signature:  Optional[str] = None,
    completed_at:        Optional[datetime] = None,
) -> None:
    """
    UPDATE transaction status and optional payment proof fields.
    Called by verify_payment, request_refund, handle_webhook, and apply_pay_later.
    """
    values: dict = {"status": status, "updated_at": datetime.utcnow()}
    if razorpay_payment_id is not None:
        values["razorpay_payment_id"] = razorpay_payment_id
    if razorpay_signature is not None:
        values["razorpay_signature"] = razorpay_signature
    if completed_at is not None:
        values["completed_at"] = completed_at

    await db.execute(update(Transaction).where(Transaction.id == txn_id).values(**values))
    await db.flush()


async def get_transaction_by_id(txn_id: UUID, db: AsyncSession) -> Optional[Transaction]:
    result = await db.execute(select(Transaction).where(Transaction.id == txn_id))
    return result.scalar_one_or_none()


async def get_transaction_by_booking_id(
    booking_id: UUID, db: AsyncSession
) -> Optional[Transaction]:
    """
    Return the latest successful transaction for a booking.
    Used by booking_repo.get_booking_with_transaction and webhook handler.
    """
    result = await db.execute(
        select(Transaction)
        .where(
            Transaction.booking_id == booking_id,
            Transaction.status     == "SUCCESS",
        )
        .order_by(Transaction.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_transaction_by_razorpay_order(
    razorpay_order_id: str, db: AsyncSession
) -> Optional[Transaction]:
    """Find transaction by Razorpay order ID — used in verify and webhook flows."""
    result = await db.execute(
        select(Transaction).where(Transaction.razorpay_order_id == razorpay_order_id)
    )
    return result.scalar_one_or_none()


async def get_transactions_by_user(
    user_id: UUID, db: AsyncSession, page: int = 1, per_page: int = 20
) -> dict:
    """Payment history for a user, newest first."""
    base  = select(Transaction).where(Transaction.user_id == user_id)
    total = await db.scalar(select(func.count()).select_from(base.subquery()))
    result = await db.execute(
        base.order_by(Transaction.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
    )
    return {"transactions": result.scalars().all(), "total": total or 0, "page": page}


# ── Saved Cards ───────────────────────────────────────────────────────────────

async def get_saved_cards(user_id: UUID, db: AsyncSession) -> List[SavedCard]:
    """All saved cards for a user, default card first."""
    result = await db.execute(
        select(SavedCard)
        .where(SavedCard.user_id == user_id)
        .order_by(SavedCard.is_default.desc())
    )
    return result.scalars().all()


async def get_card_by_id(card_id: UUID, db: AsyncSession) -> Optional[SavedCard]:
    result = await db.execute(select(SavedCard).where(SavedCard.id == card_id))
    return result.scalar_one_or_none()


# ── Refunds ───────────────────────────────────────────────────────────────────

async def create_refund(db: AsyncSession, data: dict) -> Refund:
    """
    INSERT a new refund row.
    Called by payment_service.request_refund instead of constructing inline.
    """
    refund = Refund(
        transaction_id     = data["transaction_id"],
        user_id            = data["user_id"],
        amount             = data["amount"],
        status             = data.get("status", "pending"),
        reason             = data.get("reason"),
        razorpay_refund_id = data.get("razorpay_refund_id"),
    )
    db.add(refund)
    await db.commit()
    await db.refresh(refund)
    return refund


async def get_refunds_by_user(user_id: UUID, db: AsyncSession) -> List[Refund]:
    """All refunds for a user, newest first."""
    result = await db.execute(
        select(Refund)
        .where(Refund.user_id == user_id)
        .order_by(Refund.created_at.desc())
    )
    return result.scalars().all()


async def get_refund_by_id(refund_id: UUID, db: AsyncSession) -> Optional[Refund]:
    result = await db.execute(select(Refund).where(Refund.id == refund_id))
    return result.scalar_one_or_none()


async def update_refund_status(
    db: AsyncSession, refund_id: UUID, status: str
) -> None:
    """UPDATE refund status — called when polling Razorpay for live status."""
    await db.execute(
        update(Refund)
        .where(Refund.id == refund_id)
        .values(status=status, updated_at=datetime.utcnow())
    )
    await db.flush()
