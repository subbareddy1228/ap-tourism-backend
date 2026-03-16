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
    SavedCardsResponse, SaveCardRequest, SaveCardResponse,
    DeleteCardResponse, SavedCardOut,
    RefundRequest, RefundResponse, RefundOut, RefundsListResponse,
    PayLaterCheckRequest, PayLaterCheckResponse,
    PayLaterApplyRequest, PayLaterApplyResponse,
)

logger = logging.getLogger(__name__)
RAZORPAY_SECRET = "your_razorpay_secret"


def get_payment_methods() -> PaymentMethodsResponse:
    methods = [
        PaymentMethodItem(id="razorpay",   name="Razorpay",          type="gateway"),
        PaymentMethodItem(id="upi",        name="UPI",               type="upi"),
        PaymentMethodItem(id="card",       name="Credit/Debit Card", type="card"),
        PaymentMethodItem(id="netbanking", name="Net Banking",       type="netbanking"),
        PaymentMethodItem(id="wallet",     name="Wallet",            type="wallet"),
        PaymentMethodItem(id="pay_later",  name="Pay Later",         type="bnpl"),
    ]
    return PaymentMethodsResponse(success=True, methods=methods)


def initiate_payment(db: Session, data: InitiatePaymentRequest) -> InitiatePaymentResponse:
    try:
        razorpay_order_id = f"order_{uuid.uuid4().hex[:16]}"
        txn = Transaction(
            user_id           = data.user_id,
            booking_id        = data.booking_id,
            amount            = data.amount,
            currency          = data.currency,
            status            = "pending",
            payment_method    = data.payment_method,
            razorpay_order_id = razorpay_order_id,
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
        return InitiatePaymentResponse(
            success=False, amount=data.amount,
            message=f"Failed to initiate payment: {str(e)}"
        )


def verify_payment(db: Session, data: VerifyPaymentRequest) -> VerifyPaymentResponse:
    txn = db.query(Transaction).filter(Transaction.id == data.transaction_id).first()
    if not txn:
        return VerifyPaymentResponse(success=False, status="not_found", message="Transaction not found.")

    body     = f"{data.razorpay_order_id}|{data.razorpay_payment_id}"
    expected = hmac.new(RAZORPAY_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
    is_valid = hmac.compare_digest(expected, data.razorpay_signature)

    if is_valid:
        txn.status = "success"
        txn.razorpay_payment_id = data.razorpay_payment_id
        txn.razorpay_signature  = data.razorpay_signature
        txn.updated_at = datetime.utcnow()
        db.commit()
        return VerifyPaymentResponse(success=True, transaction_id=txn.id, status="success", message="Payment verified successfully.")
    else:
        txn.status     = "failed"
        txn.updated_at = datetime.utcnow()
        db.commit()
        return VerifyPaymentResponse(success=False, transaction_id=txn.id, status="failed", message="Signature verification failed.")


def get_payment_history(db: Session, user_id: UUID) -> PaymentHistoryResponse:
    txns = db.query(Transaction).filter(
        Transaction.user_id == user_id
    ).order_by(Transaction.created_at.desc()).all()
    return PaymentHistoryResponse(
        success=True,
        transactions=[TransactionOut.model_validate(t) for t in txns],
        total=len(txns),
    )


def get_transaction(db: Session, transaction_id: UUID) -> Optional[TransactionOut]:
    txn = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not txn:
        return None
    return TransactionOut.model_validate(txn)


def validate_upi(data: ValidateUPIRequest) -> ValidateUPIResponse:
    upi      = data.upi_id.strip()
    is_valid = "@" in upi and len(upi) > 3
    return ValidateUPIResponse(
        success=True, upi_id=upi, is_valid=is_valid,
        name="Account Holder" if is_valid else None,
        message="UPI ID is valid." if is_valid else "Invalid UPI ID format.",
    )


def get_saved_cards(db: Session, user_id: UUID) -> SavedCardsResponse:
    cards = db.query(SavedCard).filter(SavedCard.user_id == user_id).all()
    return SavedCardsResponse(
        success=True,
        cards=[SavedCardOut.model_validate(c) for c in cards],
    )


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
        return SaveCardResponse(
            success=True,
            card=SavedCardOut.model_validate(card),
            message="Card saved successfully.",
        )
    except Exception as e:
        db.rollback()
        return SaveCardResponse(success=False, message=f"Failed to save card: {str(e)}")


def delete_saved_card(db: Session, card_id: UUID, user_id: UUID) -> DeleteCardResponse:
    card = db.query(SavedCard).filter(
        SavedCard.id == card_id,
        SavedCard.user_id == user_id,
    ).first()
    if not card:
        return DeleteCardResponse(success=False, message="Card not found.")
    db.delete(card)
    db.commit()
    return DeleteCardResponse(success=True, message="Card deleted successfully.")


def request_refund(db: Session, data: RefundRequest) -> RefundResponse:
    txn = db.query(Transaction).filter(
        Transaction.id == data.transaction_id,
        Transaction.user_id == data.user_id,
    ).first()
    if not txn:
        return RefundResponse(success=False, message="Transaction not found.")
    if txn.status != "success":
        return RefundResponse(success=False, message="Only successful transactions can be refunded.")
    try:
        refund = Refund(
            transaction_id = txn.id,
            user_id        = data.user_id,
            amount         = data.amount or txn.amount,
            status         = "pending",
            reason         = data.reason,
        )
        db.add(refund)
        txn.status     = "refunded"
        txn.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(refund)
        return RefundResponse(
            success=True,
            refund=RefundOut.model_validate(refund),
            message="Refund request submitted successfully.",
        )
    except Exception as e:
        db.rollback()
        return RefundResponse(success=False, message=f"Refund failed: {str(e)}")


def get_refund(db: Session, refund_id: UUID) -> RefundResponse:
    refund = db.query(Refund).filter(Refund.id == refund_id).first()
    if not refund:
        return RefundResponse(success=False, message="Refund not found.")
    return RefundResponse(success=True, refund=RefundOut.model_validate(refund), message="Refund fetched.")


def get_refunds(db: Session, user_id: UUID) -> RefundsListResponse:
    refunds = db.query(Refund).filter(Refund.user_id == user_id).order_by(Refund.created_at.desc()).all()
    return RefundsListResponse(
        success=True,
        refunds=[RefundOut.model_validate(r) for r in refunds],
        total=len(refunds),
    )


def check_pay_later(data: PayLaterCheckRequest) -> PayLaterCheckResponse:
    credit_limit    = 10000.0
    available_limit = 10000.0
    eligible        = data.amount <= available_limit
    return PayLaterCheckResponse(
        success=True, eligible=eligible,
        credit_limit=credit_limit, available_limit=available_limit,
        message="Eligible for Pay Later." if eligible else f"Amount exceeds limit of Rs.{available_limit:.0f}.",
    )


def apply_pay_later(db: Session, data: PayLaterApplyRequest) -> PayLaterApplyResponse:
    try:
        due_date = datetime.utcnow() + timedelta(days=30)
        txn = Transaction(
            user_id        = data.user_id,
            booking_id     = data.booking_id,
            amount         = data.amount,
            currency       = "INR",
            status         = "pay_later",
            payment_method = "pay_later",
        )
        db.add(txn)
        db.commit()
        db.refresh(txn)
        return PayLaterApplyResponse(
            success=True, transaction_id=txn.id,
            amount=data.amount, due_date=due_date,
            message=f"Pay Later applied. Due date: {due_date.date()}",
        )
    except Exception as e:
        db.rollback()
        return PayLaterApplyResponse(success=False, amount=data.amount, message=f"Pay Later failed: {str(e)}")


def handle_webhook(db: Session, payload: dict) -> dict:
    event = payload.get("event", "")
    if event == "payment.captured":
        order_id   = payload.get("payload", {}).get("payment", {}).get("entity", {}).get("order_id")
        payment_id = payload.get("payload", {}).get("payment", {}).get("entity", {}).get("id")
        if order_id:
            txn = db.query(Transaction).filter(Transaction.razorpay_order_id == order_id).first()
            if txn:
                txn.status = "success"
                txn.razorpay_payment_id = payment_id
                txn.updated_at = datetime.utcnow()
                db.commit()
    elif event == "refund.processed":
        payment_id = payload.get("payload", {}).get("refund", {}).get("entity", {}).get("payment_id")
        refund_id  = payload.get("payload", {}).get("refund", {}).get("entity", {}).get("id")
        if payment_id:
            txn = db.query(Transaction).filter(Transaction.razorpay_payment_id == payment_id).first()
            if txn:
                refund = db.query(Refund).filter(Refund.transaction_id == txn.id).first()
                if refund:
                    refund.status             = "processed"
                    refund.razorpay_refund_id = refund_id
                    db.commit()
    return {"success": True, "event": event, "message": "Webhook processed."}