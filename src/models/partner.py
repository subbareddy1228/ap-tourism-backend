from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Enum, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from src.api.deps.database import Base


class PartnerType(str, enum.Enum):
    HOTEL = "HOTEL"
    VEHICLE = "VEHICLE"
    GUIDE = "GUIDE"
    RESTAURANT = "RESTAURANT"


class PartnerStatus(str, enum.Enum):
    APPLIED = "APPLIED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"


class DocumentType(str, enum.Enum):
    GSTIN = "GSTIN"
    PAN = "PAN"
    AADHAAR = "AADHAAR"
    TRADE_LICENSE = "TRADE_LICENSE"
    BANK_STATEMENT = "BANK_STATEMENT"


class PayoutStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Partner(Base):
    __tablename__ = "partners"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)  # LEV146 will add ForeignKey later

    # Business Info
    partner_type = Column(Enum(PartnerType), nullable=False)
    business_name = Column(String(255), nullable=False)
    gstin = Column(String(15), nullable=True)
    pan = Column(String(10), nullable=True)

    # Verification
    verification_status = Column(Enum(PartnerStatus), default=PartnerStatus.APPLIED)
    is_active = Column(Boolean, default=True)

    # Financial
    commission_rate = Column(Float, default=10.0)
    total_earnings = Column(Float, default=0.0)
    wallet_balance = Column(Float, default=0.0)

    # Bank Details
    bank_account_number = Column(String(20), nullable=True)
    bank_ifsc = Column(String(11), nullable=True)
    bank_account_holder = Column(String(255), nullable=True)

    # Settings
    auto_accept_bookings = Column(Boolean, default=False)
    notification_preferences = Column(JSON, default={})
    unavailable_dates = Column(JSON, default=[])

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    documents = relationship("PartnerDocument", back_populates="partner")
    payouts = relationship("PartnerPayout", back_populates="partner")


class PartnerDocument(Base):
    __tablename__ = "partner_documents"

    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(Integer, ForeignKey("partners.id"), nullable=False)
    document_type = Column(Enum(DocumentType), nullable=False)
    file_url = Column(String(500), nullable=False)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    partner = relationship("Partner", back_populates="documents")


class PartnerPayout(Base):
    __tablename__ = "partner_payouts"

    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(Integer, ForeignKey("partners.id"), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(Enum(PayoutStatus), nullable=True)
    reference_id = Column(String(100), nullable=True)
    bank_account = Column(String(50), nullable=True)
    transfer_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True)

    partner = relationship("Partner", back_populates="payouts")
