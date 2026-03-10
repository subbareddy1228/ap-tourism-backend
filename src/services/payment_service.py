import hashlib, hmac, json, logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Tuple
from uuid import UUID
import razorpay
from sqlalchemy.orm import Session
from src.core.config import settings
from src.models.transaction import PaymentMethod, PaymentStatus, RefundStatus, Refund, SavedCard, Transaction
from src.schemas.payment import PaymentInitiateRequest, PaymentVerifyRequest, RefundRequestSchema, SaveCardRequest, PayLaterCheckRequest, PayLaterApplyRequest

logger = logging.getLogger(__name__)

def _rz():
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

def _hmac_str(secret, message):
    return hmac.new(key=secret.encode("utf-8"), msg=message.encode("utf-8"), digestmod=hashlib.sha256).hexdigest()

def _hmac_bytes(secret, payload):
    return hmac.new(key=secret.encode("utf-8"), msg=payload, digestmod=hashlib.sha256).hexdigest()

class PaymentService:
    @staticmethod
    def initiate(db: Session, user_id: UUID, data: PaymentInitiateRequest) -> Transaction:
        from src.models.booking import Booking
        booking = db.query(Booking).filter(Booking.id == data.booking_id, Booking.user_id == user_id).first()
        if not booking:
            raise ValueError("Booking not found or does not belong to this user.")
        existing = db.query(Transaction).filter(Transaction.booking_id == data.booking_id, Transaction.status == PaymentStatus.INITIATED).first()
        if existing:
            return existing
        rz_order = _rz().order.create({"amount": int(booking.total_amount * 100), "currency": "INR", "receipt": str(data.booking_id), "payment_capture": 1})
        tx = Transaction(booking_id=data.booking_id, user_id=user_id, razorpay_order_id=rz_order["id"], amount=booking.total_amount, currency="INR", status=PaymentStatus.INITIATED, payment_method=data.payment_method)
        db.add(tx); db.commit(); db.refresh(tx)
        return tx

    @staticmethod
    def verify(db: Session, user_id: UUID, data: PaymentVerifyRequest) -> Transaction:
        tx = db.query(Transaction).filter(Transaction.razorpay_order_id == data.razorpay_order_id, Transaction.user_id == user_id).first()
        if not tx:
            raise ValueError("Transaction not found.")
        expected = _hmac_str(settings.RAZORPAY_KEY_SECRET, f"{data.razorpay_order_id}|{data.razorpay_payment_id}")
        if not hmac.compare_digest(expected, data.razorpay_signature):
            tx.status = PaymentStatus.FAILED; db.commit()
            raise ValueError("Invalid payment signature.")
        tx.razorpay_payment_id = data.razorpay_payment_id
        tx.razorpay_signature  = data.razorpay_signature
        tx.status              = PaymentStatus.SUCCESS
        tx.completed_at        = datetime.utcnow()
        from src.models.booking import Booking, BookingStatus
        booking = db.query(Booking).filter(Booking.id == tx.booking_id).first()
        if booking:
            booking.status = BookingStatus.CONFIRMED
        db.commit(); db.refresh(tx)
        return tx

    @staticmethod
    def get_transaction(db: Session, user_id: UUID, transaction_id: UUID) -> Transaction:
        tx = db.query(Transaction).filter(Transaction.id == transaction_id, Transaction.user_id == user_id).first()
        if not tx:
            raise ValueError("Transaction not found.")
        return tx

    @staticmethod
    def get_history(db: Session, user_id: UUID, page: int, limit: int):
        q = db.query(Transaction).filter(Transaction.user_id == user_id)
        total = q.count()
        items = q.order_by(Transaction.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
        return total, items

    @staticmethod
    def handle_webhook(db: Session, payload: bytes, signature: str) -> dict:
        expected = _hmac_bytes(settings.RAZORPAY_WEBHOOK_SECRET, payload)
        if not hmac.compare_digest(expected, signature):
            raise ValueError("Invalid webhook signature.")
        event_data = json.loads(payload)
        event = event_data.get("event", "")
        if event == "payment.captured":
            entity = event_data["payload"]["payment"]["entity"]
            tx = db.query(Transaction).filter(Transaction.razorpay_order_id == entity.get("order_id")).first()
            if tx and tx.status != PaymentStatus.SUCCESS:
                tx.status = PaymentStatus.SUCCESS; tx.razorpay_payment_id = entity.get("id"); tx.completed_at = datetime.utcnow(); db.commit()
        elif event == "payment.failed":
            entity = event_data["payload"]["payment"]["entity"]
            tx = db.query(Transaction).filter(Transaction.razorpay_order_id == entity.get("order_id")).first()
            if tx: tx.status = PaymentStatus.FAILED; db.commit()
        elif event == "refund.processed":
            entity = event_data["payload"]["refund"]["entity"]
            refund = db.query(Refund).filter(Refund.razorpay_refund_id == entity.get("id")).first()
            if refund: refund.status = RefundStatus.SUCCESS; refund.processed_at = datetime.utcnow(); db.commit()
        return {"status": "ok"}

class RefundService:
    @staticmethod
    def request_refund(db: Session, user_id: UUID, data: RefundRequestSchema) -> Refund:
        tx = db.query(Transaction).filter(Transaction.booking_id == data.booking_id, Transaction.user_id == user_id, Transaction.status == PaymentStatus.SUCCESS).first()
        if not tx:
            raise ValueError("No successful payment found for this booking.")
        existing = db.query(Refund).filter(Refund.transaction_id == tx.id, Refund.status.in_([RefundStatus.PENDING, RefundStatus.PROCESSING, RefundStatus.SUCCESS])).first()
        if existing:
            raise ValueError("Refund already requested for this booking.")
        rz_refund = _rz().payment.refund(tx.razorpay_payment_id, {"amount": int(tx.amount * 100), "notes": {"reason": data.reason or "User cancellation"}})
        refund = Refund(transaction_id=tx.id, user_id=user_id, booking_id=data.booking_id, razorpay_refund_id=rz_refund.get("id"), amount=tx.amount, status=RefundStatus.PROCESSING, reason=data.reason, notes=data.notes)
        db.add(refund); tx.status = PaymentStatus.REFUNDED; db.commit(); db.refresh(refund)
        return refund

    @staticmethod
    def get_refund(db: Session, user_id: UUID, refund_id: UUID) -> Refund:
        refund = db.query(Refund).filter(Refund.id == refund_id, Refund.user_id == user_id).first()
        if not refund:
            raise ValueError("Refund not found.")
        if refund.status in (RefundStatus.PENDING, RefundStatus.PROCESSING) and refund.razorpay_refund_id:
            try:
                rz = _rz().refund.fetch(refund.razorpay_refund_id)
                if rz.get("status") == "processed":
                    refund.status = RefundStatus.SUCCESS; refund.processed_at = datetime.utcnow(); db.commit()
                elif rz.get("status") == "failed":
                    refund.status = RefundStatus.FAILED; db.commit()
            except Exception as e:
                logger.warning("Razorpay refund poll error: %s", e)
        return refund

    @staticmethod
    def get_user_refunds(db: Session, user_id: UUID):
        return db.query(Refund).filter(Refund.user_id == user_id).order_by(Refund.created_at.desc()).all()

class PaymentMethodService:
    METHODS = [
        {"method": "UPI",         "display_name": "UPI",              "enabled": True},
        {"method": "CARD",        "display_name": "Credit/Debit Card", "enabled": True},
        {"method": "NET_BANKING", "display_name": "Net Banking",       "enabled": True},
        {"method": "WALLET",      "display_name": "Wallet",            "enabled": True},
        {"method": "EMI",         "display_name": "EMI",               "enabled": True},
        {"method": "PAY_LATER",   "display_name": "Pay Later",         "enabled": True},
    ]
    @classmethod
    def get_methods(cls): return cls.METHODS

    @staticmethod
    def validate_upi(upi_id: str):
        try:
            result = _rz().payment.validate_vpa({"vpa": upi_id})
            return {"upi_id": upi_id, "is_valid": result.get("success", False), "name": result.get("customer_name")}
        except:
            return {"upi_id": upi_id, "is_valid": False, "name": None}

    @staticmethod
    def get_saved_cards(db: Session, user_id: UUID):
        return db.query(SavedCard).filter(SavedCard.user_id == user_id).order_by(SavedCard.created_at.desc()).all()

    @staticmethod
    def save_card(db: Session, user_id: UUID, data: SaveCardRequest):
        if data.is_default:
            db.query(SavedCard).filter(SavedCard.user_id == user_id, SavedCard.is_default == True).update({"is_default": False})
        card = SavedCard(user_id=user_id, razorpay_token=data.razorpay_token, card_name=data.card_name, is_default=data.is_default)
        db.add(card); db.commit(); db.refresh(card)
        return card

    @staticmethod
    def delete_card(db: Session, user_id: UUID, card_id: UUID):
        card = db.query(SavedCard).filter(SavedCard.id == card_id, SavedCard.user_id == user_id).first()
        if not card: raise ValueError("Saved card not found.")
        db.delete(card); db.commit()

class PayLaterService:
    @staticmethod
    def check_eligibility(db: Session, user_id: UUID, data: PayLaterCheckRequest):
        from src.models.booking import Booking, BookingStatus
        from src.models.user import User
        user = db.query(User).filter(User.id == user_id).first()
        if not user: return {"eligible": False, "reason": "User not found.", "deferred_days": 14}
        if not getattr(user, "phone_verified", False): return {"eligible": False, "reason": "Phone number not verified.", "deferred_days": 14}
        count = db.query(Booking).filter(Booking.user_id == user_id, Booking.status == BookingStatus.CONFIRMED).count()
        if count < 1: return {"eligible": False, "reason": "No previous confirmed bookings.", "deferred_days": 14}
        return {"eligible": True, "reason": None, "deferred_days": 14}

    @staticmethod
    def apply_pay_later(db: Session, user_id: UUID, data: PayLaterApplyRequest):
        from src.models.booking import Booking
        booking = db.query(Booking).filter(Booking.id == data.booking_id, Booking.user_id == user_id).first()
        if not booking: raise ValueError("Booking not found.")
        due_date = datetime.utcnow() + timedelta(days=data.deferred_days)
        tx = Transaction(booking_id=data.booking_id, user_id=user_id, amount=booking.total_amount, currency="INR", status=PaymentStatus.PENDING, payment_method=PaymentMethod.PAY_LATER, payment_metadata=json.dumps({"due_date": due_date.isoformat()}))
        db.add(tx); db.commit(); db.refresh(tx)
        return tx, due_date