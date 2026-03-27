"""
repositories/wallet_repo.py
Database access layer for Wallet, WalletTransaction, WithdrawalRequest.
Called by wallet_service.py for all DB reads/writes.
"""

from typing import Optional, List
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.models.wallet import Wallet, WalletTransaction, WithdrawalRequest


# ─────────────────────────── WALLET ───────────────────────────

async def get_wallet_by_user(user_id: UUID, db: AsyncSession) -> Optional[Wallet]:
    """Fetch wallet for a user. Returns None if not created yet."""
    result = await db.execute(
        select(Wallet).where(Wallet.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_wallet_by_id(wallet_id: UUID, db: AsyncSession) -> Optional[Wallet]:
    """Fetch wallet by primary key."""
    result = await db.execute(
        select(Wallet).where(Wallet.id == wallet_id)
    )
    return result.scalar_one_or_none()


async def create_wallet(user_id: UUID, db: AsyncSession) -> Wallet:
    """Create a new wallet for a user with zero balance."""
    wallet = Wallet(user_id=user_id, balance=Decimal("0.00"), status="active")
    db.add(wallet)
    await db.commit()
    await db.refresh(wallet)
    return wallet


# ─────────────────────────── TRANSACTIONS ─────────────────────

async def get_transactions(
    wallet_id: UUID,
    db: AsyncSession,
    page: int = 1,
    per_page: int = 20,
    txn_type: Optional[str] = None,
    category: Optional[str] = None,
) -> dict:
    """Paginated list of transactions for a wallet."""
    query = select(WalletTransaction).where(
        WalletTransaction.wallet_id == wallet_id
    )
    if txn_type:
        query = query.where(WalletTransaction.type == txn_type)
    if category:
        query = query.where(WalletTransaction.category == category)

    total = await db.scalar(
        select(func.count()).select_from(query.subquery())
    )
    result = await db.execute(
        query.order_by(WalletTransaction.created_at.desc())
             .offset((page - 1) * per_page)
             .limit(per_page)
    )
    return {
        "transactions": result.scalars().all(),
        "total": total or 0,
        "page": page,
        "per_page": per_page,
    }


async def get_transaction_by_id(
    txn_id: UUID, wallet_id: UUID, db: AsyncSession
) -> Optional[WalletTransaction]:
    """Get single transaction — ownership verified via wallet_id."""
    result = await db.execute(
        select(WalletTransaction).where(
            WalletTransaction.id == txn_id,
            WalletTransaction.wallet_id == wallet_id
        )
    )
    return result.scalar_one_or_none()


async def get_transaction_by_reference(
    reference_id: str, db: AsyncSession
) -> Optional[WalletTransaction]:
    """Find transaction by Razorpay payment_id — idempotency check."""
    result = await db.execute(
        select(WalletTransaction).where(
            WalletTransaction.reference_id == reference_id
        )
    )
    return result.scalar_one_or_none()


# ─────────────────────────── WITHDRAWALS ──────────────────────

async def get_withdrawals(
    wallet_id: UUID, db: AsyncSession, page: int = 1, per_page: int = 10
) -> dict:
    """Paginated list of withdrawal requests for a wallet."""
    query = select(WithdrawalRequest).where(
        WithdrawalRequest.wallet_id == wallet_id
    )
    total = await db.scalar(
        select(func.count()).select_from(query.subquery())
    )
    result = await db.execute(
        query.order_by(WithdrawalRequest.created_at.desc())
             .offset((page - 1) * per_page)
             .limit(per_page)
    )
    return {"requests": result.scalars().all(), "total": total or 0}