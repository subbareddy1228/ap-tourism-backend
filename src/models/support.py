"""
models/support.py
SQLAlchemy models for M17 — Support APIs.
Owner: LEV156 Ram Kishore Pawar

Tables:
    support_tickets   — customer support tickets
    ticket_messages   — threaded messages on each ticket
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Boolean, DateTime,
    Text, ForeignKey, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from src.core.database import Base


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Human-readable ticket number shown to users e.g. TKT-20260324-0001
    ticket_number = Column(String(30), unique=True, nullable=False, index=True)

    # Category: booking | payment | refund | guide | hotel | vehicle | app | other
    category = Column(String(50), nullable=False)

    subject  = Column(String(200), nullable=False)
    priority = Column(String(20),  nullable=False, default="medium")
    # Priority values: low | medium | high | urgent

    # Status flow: open → in_progress → resolved | closed | reopened
    status = Column(String(30), nullable=False, default="open")

    # Optional FK to a booking this ticket is about
    booking_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Admin who is handling this ticket
    assigned_to = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Timestamps for SLA tracking
    created_at   = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at  = Column(DateTime, nullable=True)
    closed_at    = Column(DateTime, nullable=True)

    # Extra metadata — e.g. {"source": "app", "platform": "android"}
    meta = Column(JSONB, nullable=True)

    messages = relationship(
        "TicketMessage",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketMessage.created_at",
    )

    __table_args__ = (
        Index("ix_support_tickets_user_status", "user_id", "status"),
        Index("ix_support_tickets_status_priority", "status", "priority"),
    )

    def __repr__(self):
        return f"<SupportTicket {self.ticket_number} status={self.status}>"


class TicketMessage(Base):
    __tablename__ = "ticket_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    ticket_id = Column(
        UUID(as_uuid=True),
        ForeignKey("support_tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    sender_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # sender_type: user | admin | system
    sender_type = Column(String(20), nullable=False, default="user")

    body = Column(Text, nullable=False)

    # Optional attachment URLs stored as a JSON array
    attachments = Column(JSONB, nullable=True)

    is_internal = Column(Boolean, default=False, nullable=False)
    # Internal notes visible only to admins, not the user

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    ticket = relationship("SupportTicket", back_populates="messages")

    def __repr__(self):
        return f"<TicketMessage ticket={self.ticket_id} sender_type={self.sender_type}>"
