# ============================================================
# app/models/user.py
# SQLAlchemy Database Models — Module 2: User APIs
# Author: Garige Sai Manvitha (LEV146)
# ============================================================

import uuid
import enum
from datetime import datetime

from sqlalchemy import (
    Column, String, Boolean, DateTime,
    Float, Text, Enum as SAEnum, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from src.core.database import Base

from src.core.database import get_db  


# ----------------------------------------------------------
# Enums
# ----------------------------------------------------------

class UserRole(str, enum.Enum):
    TRAVELER = "TRAVELER"
    GUIDE    = "GUIDE"
    ADMIN    = "ADMIN"
    SUPPORT  = "SUPPORT"


class KYCStatus(str, enum.Enum):
    PENDING  = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class Gender(str, enum.Enum):
    MALE   = "MALE"
    FEMALE = "FEMALE"
    OTHER  = "OTHER"


class Language(str, enum.Enum):
    TELUGU  = "TELUGU"
    HINDI   = "HINDI"
    ENGLISH = "ENGLISH"
    TAMIL   = "TAMIL"
    KANNADA = "KANNADA"


# ----------------------------------------------------------
# User Table
# ----------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    phone            = Column(String(15),  unique=True, nullable=False, index=True)
    email            = Column(String(255), unique=True, nullable=True,  index=True)
    hashed_password  = Column(String(255), nullable=True)

    full_name        = Column(String(200), nullable=True)
    gender           = Column(SAEnum(Gender), nullable=True)
    date_of_birth    = Column(DateTime, nullable=True)
    language         = Column(SAEnum(Language), default=Language.TELUGU, nullable=False)

    avatar_url       = Column(String(500), nullable=True)

    role             = Column(SAEnum(UserRole), default=UserRole.TRAVELER, nullable=False)

    phone_verified   = Column(Boolean, default=False, nullable=False)
    email_verified   = Column(Boolean, default=False, nullable=False)
    kyc_status       = Column(SAEnum(KYCStatus), default=KYCStatus.PENDING, nullable=False)

    wallet_balance   = Column(Float, default=0.0, nullable=False)
    fcm_token        = Column(String(500), nullable=True)         # Firebase push token

    preferences      = Column(JSON, nullable=True)                # JSONB column for travel prefs

    is_active        = Column(Boolean, default=True, nullable=False)
    deleted_at       = Column(DateTime, nullable=True)            # Soft delete timestamp

    created_at       = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<User id={self.id} phone={self.phone} role={self.role}>"


# ----------------------------------------------------------
# Address Table
# ----------------------------------------------------------

class AddressLabel(str, enum.Enum):
    HOME  = "HOME"
    WORK  = "WORK"
    OTHER = "OTHER"


class Address(Base):
    __tablename__ = "addresses"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id       = Column(UUID(as_uuid=True), nullable=False, index=True)

    label         = Column(SAEnum(AddressLabel), default=AddressLabel.HOME, nullable=False)
    address_line1 = Column(String(255), nullable=False)
    address_line2 = Column(String(255), nullable=True)
    city          = Column(String(100), nullable=False)
    state         = Column(String(100), nullable=False)
    pincode       = Column(String(10),  nullable=False)

    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Address id={self.id} user_id={self.user_id} city={self.city}>"


# ----------------------------------------------------------
# Family Member Table
# ----------------------------------------------------------

class Relation(str, enum.Enum):
    SPOUSE  = "SPOUSE"
    CHILD   = "CHILD"
    PARENT  = "PARENT"
    SIBLING = "SIBLING"
    OTHER   = "OTHER"


class IDProofType(str, enum.Enum):
    AADHAR   = "AADHAR"
    PAN      = "PAN"
    PASSPORT = "PASSPORT"
    VOTER_ID = "VOTER_ID"


class FamilyMember(Base):
    __tablename__ = "family_members"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id         = Column(UUID(as_uuid=True), nullable=False, index=True)

    name            = Column(String(200), nullable=False)
    relation        = Column(SAEnum(Relation), nullable=False)
    date_of_birth   = Column(DateTime, nullable=True)
    gender          = Column(SAEnum(Gender), nullable=True)

    id_proof_type   = Column(SAEnum(IDProofType), nullable=True)
    id_proof_number = Column(String(100), nullable=True)

    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<FamilyMember id={self.id} name={self.name} relation={self.relation}>"
