"""

models/partner.py

Partner module models:

  - Partner         (main profile)

  - PartnerDocument (KYC documents)

  - PartnerPayout   (payout history)

  - PartnerBankDetails (bank account)

"""
 
import uuid

from datetime import datetime

from sqlalchemy import (

    Column, String, Boolean, DateTime, Text,

    ForeignKey, JSON, Float, Numeric, Date

)

from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.orm import relationship

from src.models.base import Base
 
 
# ══════════════════ PARTNER ══════════════════
 
class Partner(Base):

    __tablename__ = "partners"
 
    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    user_id             = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
 
    # ── Business Info ─────────────────────────────────────────

    business_name       = Column(String(200), nullable=False)

    business_type       = Column(String(50), nullable=False)

    # types: HOTEL | VEHICLE | GUIDE
 
    gstin               = Column(String(15), nullable=True)

    pan                 = Column(String(10), nullable=True)

    description         = Column(Text, nullable=True)

    logo_url            = Column(Text, nullable=True)
 
    # ── Contact ───────────────────────────────────────────────

    contact_phone       = Column(String(15), nullable=True)

    contact_email       = Column(String(255), nullable=True)

    website             = Column(String(255), nullable=True)
 
    # ── Location ──────────────────────────────────────────────

    address             = Column(Text, nullable=True)

    city                = Column(String(100), nullable=True)

    state               = Column(String(100), nullable=True)

    pincode             = Column(String(10), nullable=True)

    latitude            = Column(Float, nullable=True)

    longitude           = Column(Float, nullable=True)
 
    # ── Verification ──────────────────────────────────────────

    verification_status = Column(String(20), default="APPLIED", nullable=False)

    # APPLIED | UNDER_REVIEW | VERIFIED | REJECTED
 
    is_active           = Column(Boolean, default=True, nullable=False)

    verified_at         = Column(DateTime, nullable=True)

    rejection_reason    = Column(Text, nullable=True)
 
    # ── Financials ────────────────────────────────────────────

    commission_rate     = Column(Float, default=10.0, nullable=False)  # percentage

    total_earnings      = Column(Numeric(12, 2), default=0, nullable=False)

    pending_payout      = Column(Numeric(12, 2), default=0, nullable=False)
 
    # ── Settings ──────────────────────────────────────────────

    auto_accept         = Column(Boolean, default=False, nullable=False)

    unavailable_dates   = Column(JSON, default=list, nullable=True)

    # ["2024-12-25", "2024-12-26"]

    notification_prefs  = Column(JSON, default=dict, nullable=True)

    # { "booking_requests": true, "payment_received": true }
 
    # ── Stats ─────────────────────────────────────────────────

    rating              = Column(Float, default=0.0, nullable=True)

    total_reviews       = Column(String(10), default="0", nullable=True)
 
    # ── Timestamps ────────────────────────────────────────────

    created_at          = Column(DateTime, default=datetime.utcnow, nullable=False)

    updated_at          = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 
    # ── Relationships ─────────────────────────────────────────

    user                = relationship("User", back_populates="partner")

    documents           = relationship("PartnerDocument", back_populates="partner", cascade="all, delete-orphan")

    payouts             = relationship("PartnerPayout", back_populates="partner", cascade="all, delete-orphan")

    bank_details        = relationship("PartnerBankDetails", back_populates="partner", uselist=False, cascade="all, delete-orphan")
 
    def __repr__(self):

        return f"<Partner {self.business_name} ({self.business_type}) status={self.verification_status}>"
 
 
# ══════════════════ PARTNER DOCUMENT ══════════════════
 
class PartnerDocument(Base):

    __tablename__ = "partner_documents"
 
    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    partner_id      = Column(UUID(as_uuid=True), ForeignKey("partners.id", ondelete="CASCADE"), nullable=False, index=True)
 
    doc_type        = Column(String(50), nullable=False)

    # GSTIN | PAN | BANK_PROOF | PROPERTY_DOC | OTHER
 
    file_url        = Column(Text, nullable=False)       # S3 URL

    file_name       = Column(String(255), nullable=True)

    is_verified     = Column(Boolean, default=False, nullable=False)

    verified_at     = Column(DateTime, nullable=True)

    notes           = Column(Text, nullable=True)
 
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)
 
    partner         = relationship("Partner", back_populates="documents")
 
    def __repr__(self):

        return f"<PartnerDocument {self.doc_type} verified={self.is_verified}>"
 
 
# ══════════════════ PARTNER PAYOUT ══════════════════
 
class PartnerPayout(Base):

    __tablename__ = "partner_payouts"
 
    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    partner_id      = Column(UUID(as_uuid=True), ForeignKey("partners.id", ondelete="CASCADE"), nullable=False, index=True)
 
    amount          = Column(Numeric(12, 2), nullable=False)

    status          = Column(String(20), default="PENDING", nullable=False)

    # PENDING | TRANSFERRED | FAILED
 
    bank_account    = Column(String(20), nullable=True)

    ifsc_code       = Column(String(11), nullable=True)

    transfer_ref    = Column(String(100), nullable=True)  # bank reference number

    transfer_date   = Column(DateTime, nullable=True)

    notes           = Column(Text, nullable=True)
 
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)

    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 
    partner         = relationship("Partner", back_populates="payouts")
 
    def __repr__(self):

        return f"<PartnerPayout ₹{self.amount} status={self.status}>"
 
 
# ══════════════════ PARTNER BANK DETAILS ══════════════════
 
class PartnerBankDetails(Base):

    __tablename__ = "partner_bank_details"
 
    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    partner_id          = Column(UUID(as_uuid=True), ForeignKey("partners.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
 
    account_number      = Column(String(20), nullable=False)

    ifsc_code           = Column(String(11), nullable=False)

    account_holder_name = Column(String(100), nullable=False)

    bank_name           = Column(String(100), nullable=True)

    branch_name         = Column(String(100), nullable=True)
 
    is_verified         = Column(Boolean, default=False, nullable=False)

    created_at          = Column(DateTime, default=datetime.utcnow, nullable=False)

    updated_at          = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 
    partner             = relationship("Partner", back_populates="bank_details")
 
    def __repr__(self):

        return f"<PartnerBankDetails account={self.account_number[-4:]} partner_id={self.partner_id}>"
 