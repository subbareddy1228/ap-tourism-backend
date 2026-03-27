"""
repositories/transaction_repo.py
DB access for Transaction, SavedCard, and Refund models.
Used by payment_service.py.
"""

from typing import Optional, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.models.transaction import Transaction, SavedCard, Refund


# ─────────────────────────── TRANSACTIONS ─────────────────────

async def get_transaction_by_id(
    txn_id: UUID, db: AsyncSession
) -> Optional[Transaction]:
    result = await db.execute(
        select(Transaction).where(Transaction.id == txn_id)
    )
    return result.scalar_one_or_none()


async def get_transactions_by_user(
    user_id: UUID, db: AsyncSession, page: int = 1, per_page: int = 20
) -> dict:
    """Payment history for a user, newest first."""
    query = select(Transaction).where(Transaction.user_id == user_id)
    total = await db.scalar(
        select(func.count()).select_from(query.subquery())
    )
    result = await db.execute(
        query.order_by(Transaction.created_at.desc())
             .offset((page - 1) * per_page)
             .limit(per_page)
    )
    return {
        "transactions": result.scalars().all(),
        "total": total or 0,
        "page": page,
    }


async def get_transaction_by_razorpay_order(
    razorpay_order_id: str, db: AsyncSession
) -> Optional[Transaction]:
    """Find transaction by Razorpay order ID for verification flow."""
    result = await db.execute(
        select(Transaction).where(
            Transaction.razorpay_order_id == razorpay_order_id
        )
    )
    return result.scalar_one_or_none()


# ─────────────────────────── SAVED CARDS ──────────────────────

async def get_saved_cards(user_id: UUID, db: AsyncSession) -> List[SavedCard]:
    """All saved cards for a user."""
    result = await db.execute(
        select(SavedCard).where(SavedCard.user_id == user_id)
                          .order_by(SavedCard.is_default.desc())
    )
    return result.scalars().all()


async def get_card_by_id(card_id: UUID, db: AsyncSession) -> Optional[SavedCard]:
    result = await db.execute(
        select(SavedCard).where(SavedCard.id == card_id)
    )
    return result.scalar_one_or_none()


# ─────────────────────────── REFUNDS ──────────────────────────

async def get_refunds_by_user(user_id: UUID, db: AsyncSession) -> List[Refund]:
    """All refunds for a user."""
    result = await db.execute(
        select(Refund).where(Refund.user_id == user_id)
                        .order_by(Refund.created_at.desc())
    )
    return result.scalars().all()


async def get_refund_by_id(refund_id: UUID, db: AsyncSession) -> Optional[Refund]:
    result = await db.execute(
        select(Refund).where(Refund.id == refund_id)
    )
    return result.scalar_one_or_none()