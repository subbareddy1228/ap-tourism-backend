import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models.transaction import Transaction, SavedCard, Refund
from src.schemas.payment import (
    InitiatePaymentRequest, InitiatePaymentResponse,
    VerifyPaymentRequest, VerifyPaymentResponse,
    TransactionOut, PaymentHistoryResponse,
    PaymentMethodsResponse, PaymentMethodItem,
    ValidateUPIRequest, ValidateUPIResponse,
    SavedCardsResponse, SaveCardRequest, SaveCardResponse, DeleteCardResponse,
    SavedCardOut,
    RefundRequest, RefundResponse, RefundOut, RefundsListResponse,
    PayLaterCheckRequest, PayLaterCheckResponse,
    PayLaterApplyRequest, PayLaterApplyResponse,
)
from src.core.config import settings
from src.integrations.razorpay import (
    create_order as rzp_create_order,
    verify_payment_signature as rzp_verify_signature,
    create_refund as rzp_create_refund,
    get_refund_status as rzp_get_refund_status,
)

logger = logging.getLogger(__name__)

METHOD_MAP = {
    "razorpay": "CARD", "upi": "UPI", "card": "CARD",
    "netbanking": "NET_BANKING", "net_banking": "NET_BANKING",
    "wallet": "WALLET", "emi": "EMI", "pay_later": "PAY_LATER",
    "UPI": "UPI", "CARD": "CARD", "NET_BANKING": "NET_BANKING",
    "WALLET": "WALLET", "EMI": "EMI", "PAY_LATER": "PAY_LATER",
}


def _map_method(method: str) -> str:
    return METHOD_MAP.get(str(method), "CARD")


# ─────────────────────────────────────────────
# PAYMENT METHODS (sync — no DB needed)
# ─────────────────────────────────────────────

async def get_payment_methods() -> PaymentMethodsResponse:
    return PaymentMethodsResponse(success=True, methods=[
        PaymentMethodItem(id="UPI",         name="UPI",               type="upi"),
        PaymentMethodItem(id="CARD",        name="Credit/Debit Card",  type="card"),
        PaymentMethodItem(id="NET_BANKING", name="Net Banking",        type="netbanking"),
        PaymentMethodItem(id="WALLET",      name="Wallet",             type="wallet"),
        PaymentMethodItem(id="EMI",         name="EMI",                type="emi"),
        PaymentMethodItem(id="PAY_LATER",   name="Pay Later",          type="bnpl"),
    ])


# ─────────────────────────────────────────────
# INITIATE
# ─────────────────────────────────────────────

async def initiate_payment(db: AsyncSession, data: InitiatePaymentRequest) -> InitiatePaymentResponse:
    try:
        # Create a real Razorpay order — returns order_id used by frontend checkout
        order = rzp_create_order(
            amount_inr=float(data.amount),
            booking_id=str(data.booking_id),
            notes=data.notes or {},
        )
        razorpay_order_id = order["id"]

        now = datetime.utcnow()
        txn = Transaction(
            booking_id        = data.booking_id,
            user_id           = data.user_id,
            amount            = data.amount,
            currency          = data.currency,
            status            = "INITIATED",
            payment_method    = _map_method(data.payment_method),
            razorpay_order_id = razorpay_order_id,
            payment_metadata  = data.notes,
            initiated_at      = now,
            created_at        = now,
            updated_at        = now,
        )
        db.add(txn)
        await db.commit()
        await db.refresh(txn)

        return InitiatePaymentResponse(
            success=True,
            transaction_id=txn.id,
            razorpay_order_id=razorpay_order_id,
            razorpay_key_id=settings.RAZORPAY_KEY_ID,   # frontend needs this for checkout
            amount=data.amount,
            currency=data.currency,
            message="Payment initiated successfully.",
        )
    except Exception as e:
        await db.rollback()
        logger.error("Initiate payment failed booking_id=%s error=%s", data.booking_id, str(e))
        return InitiatePaymentResponse(success=False, amount=data.amount, message=f"Failed: {str(e)}")


# ─────────────────────────────────────────────
# VERIFY
# ─────────────────────────────────────────────

async def verify_payment(db: AsyncSession, data: VerifyPaymentRequest) -> VerifyPaymentResponse:
    result = await db.execute(select(Transaction).where(Transaction.id == data.transaction_id))
    txn = result.scalar_one_or_none()
    if not txn:
        return VerifyPaymentResponse(success=False, status="not_found", message="Transaction not found.")

    # Use integration layer — keeps signature logic in one place
    is_valid = rzp_verify_signature(
        razorpay_order_id=data.razorpay_order_id,
        razorpay_payment_id=data.razorpay_payment_id,
        razorpay_signature=data.razorpay_signature,
    )
    now = datetime.utcnow()

    if is_valid:

        txn.status = "SUCCESS"

        txn.razorpay_payment_id = data.razorpay_payment_id

        txn.razorpay_signature = data.razorpay_signature

        txn.completed_at = now

        txn.updated_at = now
 
        # Update linked booking status to CONFIRMED

        from src.models.booking import Booking

        from src.common.enums import BookingStatus, PaymentStatus

        booking_result = await db.execute(

            select(Booking).where(Booking.id == txn.booking_id)

        )

        booking = booking_result.scalar_one_or_none()

        if booking:

            booking.status = BookingStatus.CONFIRMED

            booking.payment_status = PaymentStatus.SUCCESS

            booking.updated_at = now
 
        await db.commit()

        return VerifyPaymentResponse(success=True, transaction_id=txn.id, status="SUCCESS", message="Payment verified.")
 
    else:
        txn.status = "FAILED"
        txn.updated_at = now
        await db.commit()
        return VerifyPaymentResponse(success=False, transaction_id=txn.id, status="FAILED", message="Signature verification failed.")


# ─────────────────────────────────────────────
# HISTORY
# ─────────────────────────────────────────────

async def get_payment_history(db: AsyncSession, user_id: UUID) -> PaymentHistoryResponse:
    result = await db.execute(
        select(Transaction).where(Transaction.user_id == user_id).order_by(Transaction.created_at.desc())
    )
    txns = result.scalars().all()
    return PaymentHistoryResponse(
        success=True,
        transactions=[TransactionOut.model_validate(t) for t in txns],
        total=len(txns),
    )


# ─────────────────────────────────────────────
# GET TRANSACTION
# ─────────────────────────────────────────────

async def get_transaction(db: AsyncSession, transaction_id: UUID) -> Optional[TransactionOut]:
    result = await db.execute(select(Transaction).where(Transaction.id == transaction_id))
    txn = result.scalar_one_or_none()
    if not txn:
        return None
    return TransactionOut.model_validate(txn)


# ─────────────────────────────────────────────
# VALIDATE UPI (sync — no DB)
# ─────────────────────────────────────────────

async def validate_upi(data: ValidateUPIRequest) -> ValidateUPIResponse:
    upi = data.upi_id.strip()
    is_valid = "@" in upi and len(upi) > 3
    return ValidateUPIResponse(
        success=True, upi_id=upi, is_valid=is_valid,
        name="Account Holder" if is_valid else None,
        message="UPI ID is valid." if is_valid else "Invalid UPI ID format.",
    )


# ─────────────────────────────────────────────
# SAVED CARDS
# ─────────────────────────────────────────────

async def get_saved_cards(db: AsyncSession, user_id: UUID) -> SavedCardsResponse:
    result = await db.execute(select(SavedCard).where(SavedCard.user_id == user_id))
    cards = result.scalars().all()
    return SavedCardsResponse(success=True, cards=[SavedCardOut.model_validate(c) for c in cards])


async def save_card(db: AsyncSession, data: SaveCardRequest) -> SaveCardResponse:
    try:
        if data.is_default:
            result = await db.execute(select(SavedCard).where(SavedCard.user_id == data.user_id))
            for c in result.scalars().all():
                c.is_default = False
        card = SavedCard(
            user_id        = data.user_id,
            razorpay_token = data.razorpay_token,
            last4          = data.last4,
            card_network   = data.card_network,
            card_name      = data.card_name,
            expiry_month   = data.expiry_month,
            expiry_year    = data.expiry_year,
            is_default     = data.is_default,
        )
        db.add(card)
        await db.commit()
        await db.refresh(card)
        return SaveCardResponse(success=True, card=SavedCardOut.model_validate(card), message="Card saved.")
    except Exception as e:
        await db.rollback()
        return SaveCardResponse(success=False, message=f"Failed: {str(e)}")


async def delete_saved_card(db: AsyncSession, card_id: UUID, user_id: UUID) -> DeleteCardResponse:
    result = await db.execute(select(SavedCard).where(SavedCard.id == card_id, SavedCard.user_id == user_id))
    card = result.scalar_one_or_none()
    if not card:
        return DeleteCardResponse(success=False, message="Card not found.")
    await db.delete(card)
    await db.commit()
    return DeleteCardResponse(success=True, message="Card deleted.")


# ─────────────────────────────────────────────
# REFUND
# ─────────────────────────────────────────────

async def request_refund(db: AsyncSession, data: RefundRequest) -> RefundResponse:
    result = await db.execute(
        select(Transaction).where(Transaction.id == data.transaction_id, Transaction.user_id == data.user_id)
    )
    txn = result.scalar_one_or_none()
    if not txn:
        return RefundResponse(success=False, message="Transaction not found.")
    if str(txn.status) != "SUCCESS":
        return RefundResponse(success=False, message="Only successful transactions can be refunded.")
    if not txn.razorpay_payment_id:
        return RefundResponse(success=False, message="No Razorpay payment ID on record — cannot refund.")

    refund_amount = data.amount or float(txn.amount)

    try:
        # Call real Razorpay refund API
        rzp_refund = rzp_create_refund(
            razorpay_payment_id=txn.razorpay_payment_id,
            amount_inr=refund_amount,
            notes={"reason": data.reason or "Customer request"},
        )

        refund = Refund(
            transaction_id     = txn.id,
            user_id            = data.user_id,
            amount             = refund_amount,
            status             = rzp_refund.get("status", "pending"),
            reason             = data.reason,
            razorpay_refund_id = rzp_refund.get("id"),   # store for status polling
        )
        db.add(refund)
        txn.status = "REFUNDED"
        txn.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(refund)
        return RefundResponse(success=True, refund=RefundOut.model_validate(refund), message="Refund initiated with Razorpay.")

    except RuntimeError as e:
        await db.rollback()
        return RefundResponse(success=False, message=str(e))
    except Exception as e:
        await db.rollback()
        return RefundResponse(success=False, message=f"Refund failed: {str(e)}")


async def get_refund(db: AsyncSession, refund_id: UUID) -> RefundResponse:
    result = await db.execute(select(Refund).where(Refund.id == refund_id))
    refund = result.scalar_one_or_none()
    if not refund:
        return RefundResponse(success=False, message="Refund not found.")

    # Poll Razorpay for live status if still pending
    if refund.status == "pending" and getattr(refund, "razorpay_refund_id", None):
        try:
            rzp_data = rzp_get_refund_status(refund.razorpay_refund_id)
            live_status = rzp_data.get("status", refund.status)
            if live_status != refund.status:
                refund.status = live_status
                await db.commit()
        except Exception:
            pass  # best-effort — return cached status on poll failure

    return RefundResponse(success=True, refund=RefundOut.model_validate(refund), message="OK")


async def get_refunds(db: AsyncSession, user_id: UUID) -> RefundsListResponse:
    result = await db.execute(select(Refund).where(Refund.user_id == user_id))
    refunds = result.scalars().all()
    return RefundsListResponse(success=True, refunds=[RefundOut.model_validate(r) for r in refunds], total=len(refunds))


# ─────────────────────────────────────────────
# PAY LATER
# ─────────────────────────────────────────────

async def check_pay_later(data: PayLaterCheckRequest) -> PayLaterCheckResponse:
    eligible = data.amount <= 10000.0
    return PayLaterCheckResponse(
        success=True, eligible=eligible,
        credit_limit=10000.0, available_limit=10000.0,
        message="Eligible." if eligible else "Amount exceeds limit.",
    )


async def apply_pay_later(db: AsyncSession, data: PayLaterApplyRequest) -> PayLaterApplyResponse:
    try:
        now = datetime.utcnow()
        due_date = now + timedelta(days=30)
        txn = Transaction(
            booking_id       = data.booking_id,
            user_id          = data.user_id,
            amount           = data.amount,
            currency         = "INR",
            status           = "INITIATED",
            payment_method   = "PAY_LATER",
            initiated_at     = now,
            created_at       = now,
            updated_at       = now,
            payment_metadata = f"Pay Later due {due_date.date()}",
        )
        db.add(txn)
        await db.commit()
        await db.refresh(txn)
        return PayLaterApplyResponse(success=True, transaction_id=txn.id, amount=data.amount, due_date=due_date, message=f"Pay Later applied. Due: {due_date.date()}")
    except Exception as e:
        await db.rollback()
        return PayLaterApplyResponse(success=False, amount=data.amount, message=f"Failed: {str(e)}")


# ─────────────────────────────────────────────
# WEBHOOK
# ─────────────────────────────────────────────

async def handle_webhook(db: AsyncSession, payload: dict) -> dict:
    event = payload.get("event", "")
    if event == "payment.captured":
        order_id = payload.get("payload", {}).get("payment", {}).get("entity", {}).get("order_id")
        pay_id   = payload.get("payload", {}).get("payment", {}).get("entity", {}).get("id")
        if order_id:
            result = await db.execute(select(Transaction).where(Transaction.razorpay_order_id == order_id))
            txn = result.scalar_one_or_none()
            if txn:
                txn.status = "SUCCESS"; txn.razorpay_payment_id = pay_id
                txn.completed_at = datetime.utcnow(); txn.updated_at = datetime.utcnow()
                await db.commit()
    return {"success": True, "event": event, "message": "Webhook processed."}