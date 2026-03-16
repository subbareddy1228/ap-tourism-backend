import hashlib
import hmac
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

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

logger = logging.getLogger(__name__)

RAZORPAY_SECRET = "your_razorpay_secret"

METHOD_MAP = {
    "razorpay":    "CARD",
    "upi":         "UPI",
    "card":        "CARD",
    "netbanking":  "NET_BANKING",
    "net_banking": "NET_BANKING",
    "wallet":      "WALLET",
    "emi":         "EMI",
    "pay_later":   "PAY_LATER",
    "UPI":         "UPI",
    "CARD":        "CARD",
    "NET_BANKING": "NET_BANKING",
    "WALLET":      "WALLET",
    "EMI":         "EMI",
    "PAY_LATER":   "PAY_LATER",
}


def _map_method(method: str) -> str:
    return METHOD_MAP.get(str(method), "CARD")


# ─────────────────────────────────────────────
# PAYMENT METHODS
# ─────────────────────────────────────────────

def get_payment_methods() -> PaymentMethodsResponse:
    methods = [
        PaymentMethodItem(id="UPI",         name="UPI",               type="upi"),
        PaymentMethodItem(id="CARD",        name="Credit/Debit Card",  type="card"),
        PaymentMethodItem(id="NET_BANKING", name="Net Banking",        type="netbanking"),
        PaymentMethodItem(id="WALLET",      name="Wallet",             type="wallet"),
        PaymentMethodItem(id="EMI",         name="EMI",                type="emi"),
        PaymentMethodItem(id="PAY_LATER",   name="Pay Later",          type="bnpl"),
    ]
    return PaymentMethodsResponse(success=True, methods=methods)


# ─────────────────────────────────────────────
# INITIATE
# ─────────────────────────────────────────────

def initiate_payment(db: Session, data: InitiatePaymentRequest) -> InitiatePaymentResponse:
    try:
        razorpay_order_id = f"order_{uuid.uuid4().hex[:16]}"
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
        db.commit()
        db.refresh(txn)
        return InitiatePaymentResponse(
            success=True, transaction_id=txn.id,
            razorpay_order_id=razorpay_order_id,
            amount=data.amount, currency=data.currency,
            message="Payment initiated successfully.",
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Initiate error: {e}")
        return InitiatePaymentResponse(success=False, amount=data.amount, message=f"Failed: {str(e)}")


# ─────────────────────────────────────────────
# VERIFY
# ─────────────────────────────────────────────

def verify_payment(db: Session, data: VerifyPaymentRequest) -> VerifyPaymentResponse:
    txn = db.query(Transaction).filter(Transaction.id == data.transaction_id).first()
    if not txn:
        return VerifyPaymentResponse(success=False, status="not_found", message="Transaction not found.")
    body     = f"{data.razorpay_order_id}|{data.razorpay_payment_id}"
    expected = hmac.new(RAZORPAY_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
    is_valid = hmac.compare_digest(expected, data.razorpay_signature)
    now = datetime.utcnow()
    if is_valid:
        txn.status = "SUCCESS"; txn.razorpay_payment_id = data.razorpay_payment_id
        txn.razorpay_signature = data.razorpay_signature
        txn.completed_at = now; txn.updated_at = now
        db.commit()
        return VerifyPaymentResponse(success=True, transaction_id=txn.id, status="SUCCESS", message="Payment verified.")
    else:
        txn.status = "FAILED"; txn.updated_at = now
        db.commit()
        return VerifyPaymentResponse(success=False, transaction_id=txn.id, status="FAILED", message="Signature verification failed.")


# ─────────────────────────────────────────────
# HISTORY
# ─────────────────────────────────────────────

def get_payment_history(db: Session, user_id: UUID) -> PaymentHistoryResponse:
    txns = db.query(Transaction).filter(Transaction.user_id == user_id).order_by(Transaction.created_at.desc()).all()
    return PaymentHistoryResponse(
        success=True,
        transactions=[TransactionOut.model_validate(t) for t in txns],
        total=len(txns),
    )


# ─────────────────────────────────────────────
# GET TRANSACTION
# ─────────────────────────────────────────────

def get_transaction(db: Session, transaction_id: UUID) -> Optional[TransactionOut]:
    txn = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not txn:
        return None
    return TransactionOut.model_validate(txn)


# ─────────────────────────────────────────────
# VALIDATE UPI
# ─────────────────────────────────────────────

def validate_upi(data: ValidateUPIRequest) -> ValidateUPIResponse:
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

def get_saved_cards(db: Session, user_id: UUID) -> SavedCardsResponse:
    cards = db.query(SavedCard).filter(SavedCard.user_id == user_id).all()
    return SavedCardsResponse(success=True, cards=[SavedCardOut.model_validate(c) for c in cards])


def save_card(db: Session, data: SaveCardRequest) -> SaveCardResponse:
    try:
        if data.is_default:
            db.query(SavedCard).filter(SavedCard.user_id == data.user_id).update({"is_default": False})
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
        db.commit()
        db.refresh(card)
        return SaveCardResponse(success=True, card=SavedCardOut.model_validate(card), message="Card saved.")
    except Exception as e:
        db.rollback()
        return SaveCardResponse(success=False, message=f"Failed: {str(e)}")


def delete_saved_card(db: Session, card_id: UUID, user_id: UUID) -> DeleteCardResponse:
    card = db.query(SavedCard).filter(SavedCard.id == card_id, SavedCard.user_id == user_id).first()
    if not card:
        return DeleteCardResponse(success=False, message="Card not found.")
    db.delete(card)
    db.commit()
    return DeleteCardResponse(success=True, message="Card deleted.")


# ─────────────────────────────────────────────
# REFUND
# ─────────────────────────────────────────────

def request_refund(db: Session, data: RefundRequest) -> RefundResponse:
    txn = db.query(Transaction).filter(
        Transaction.id == data.transaction_id,
        Transaction.user_id == data.user_id,
    ).first()
    if not txn:
        return RefundResponse(success=False, message="Transaction not found.")
    if str(txn.status) != "SUCCESS":
        return RefundResponse(success=False, message="Only successful transactions can be refunded.")
    try:
        refund = Refund(
            transaction_id = txn.id,
            user_id        = data.user_id,
            amount         = data.amount or float(txn.amount),
            status         = "pending",
            reason         = data.reason,
        )
        db.add(refund)
        txn.status = "REFUNDED"; txn.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(refund)
        return RefundResponse(success=True, refund=RefundOut.model_validate(refund), message="Refund submitted.")
    except Exception as e:
        db.rollback()
        return RefundResponse(success=False, message=f"Refund failed: {str(e)}")


def get_refund(db: Session, refund_id: UUID) -> RefundResponse:
    refund = db.query(Refund).filter(Refund.id == refund_id).first()
    if not refund:
        return RefundResponse(success=False, message="Refund not found.")
    return RefundResponse(success=True, refund=RefundOut.model_validate(refund), message="OK")


def get_refunds(db: Session, user_id: UUID) -> RefundsListResponse:
    refunds = db.query(Refund).filter(Refund.user_id == user_id).all()
    return RefundsListResponse(success=True, refunds=[RefundOut.model_validate(r) for r in refunds], total=len(refunds))


# ─────────────────────────────────────────────
# PAY LATER
# ─────────────────────────────────────────────

def check_pay_later(data: PayLaterCheckRequest) -> PayLaterCheckResponse:
    eligible = data.amount <= 10000.0
    return PayLaterCheckResponse(
        success=True, eligible=eligible,
        credit_limit=10000.0, available_limit=10000.0,
        message="Eligible." if eligible else "Amount exceeds limit.",
    )


def apply_pay_later(db: Session, data: PayLaterApplyRequest) -> PayLaterApplyResponse:
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
        db.commit()
        db.refresh(txn)
        return PayLaterApplyResponse(success=True, transaction_id=txn.id, amount=data.amount, due_date=due_date, message=f"Pay Later applied. Due: {due_date.date()}")
    except Exception as e:
        db.rollback()
        return PayLaterApplyResponse(success=False, amount=data.amount, message=f"Failed: {str(e)}")


# ─────────────────────────────────────────────
# WEBHOOK
# ─────────────────────────────────────────────

def handle_webhook(db: Session, payload: dict) -> dict:
    event = payload.get("event", "")
    if event == "payment.captured":
        order_id = payload.get("payload", {}).get("payment", {}).get("entity", {}).get("order_id")
        pay_id   = payload.get("payload", {}).get("payment", {}).get("entity", {}).get("id")
        if order_id:
            txn = db.query(Transaction).filter(Transaction.razorpay_order_id == order_id).first()
            if txn:
                txn.status = "SUCCESS"; txn.razorpay_payment_id = pay_id
                txn.completed_at = datetime.utcnow(); txn.updated_at = datetime.utcnow()
                db.commit()
    return {"success": True, "event": event, "message": "Webhook processed."}