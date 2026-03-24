"""
schemas/support.py
Pydantic schemas for M17 — Support APIs.
Owner: LEV156 Ram Kishore Pawar
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, field_validator


# ═══════════════════════════════════════════════════════════════
# REQUEST SCHEMAS
# ═══════════════════════════════════════════════════════════════

class CreateTicketRequest(BaseModel):
    """POST /support/tickets — user creates a new ticket."""
    category:   str
    subject:    str
    body:       str                         # first message content
    priority:   str = "medium"
    booking_id: Optional[UUID] = None      # attach ticket to a specific booking

    @field_validator("category")
    def category_valid(cls, v: str) -> str:
        allowed = {"booking", "payment", "refund", "guide", "hotel", "vehicle", "app", "other"}
        if v not in allowed:
            raise ValueError(f"category must be one of {allowed}")
        return v

    @field_validator("priority")
    def priority_valid(cls, v: str) -> str:
        allowed = {"low", "medium", "high", "urgent"}
        if v not in allowed:
            raise ValueError(f"priority must be one of {allowed}")
        return v

    @field_validator("subject")
    def subject_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("subject cannot be empty")
        if len(v) > 200:
            raise ValueError("subject cannot exceed 200 characters")
        return v

    @field_validator("body")
    def body_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("message body cannot be empty")
        return v


class AddMessageRequest(BaseModel):
    """POST /support/tickets/{id}/messages — add a reply to a ticket."""
    body:        str
    is_internal: bool = False   # admin-only internal notes
    attachments: Optional[List[str]] = None  # list of S3 URLs

    @field_validator("body")
    def body_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("message body cannot be empty")
        return v


class AssignTicketRequest(BaseModel):
    """PUT /support/tickets/{id}/assign — admin assigns ticket to a user."""
    assigned_to: UUID   # admin user_id


class ResolveTicketRequest(BaseModel):
    """PUT /support/tickets/{id}/resolve — admin resolves ticket."""
    resolution_note: Optional[str] = None   # optional closing message to user


# ═══════════════════════════════════════════════════════════════
# RESPONSE SCHEMAS
# ═══════════════════════════════════════════════════════════════

class TicketMessageResponse(BaseModel):
    """Single message in a ticket thread."""
    id:          UUID
    sender_id:   UUID
    sender_type: str
    body:        str
    attachments: Optional[List[str]]
    is_internal: bool
    created_at:  datetime

    class Config:
        from_attributes = True


class TicketResponse(BaseModel):
    """Full ticket with messages — returned by create and get-by-id."""
    id:            UUID
    ticket_number: str
    category:      str
    subject:       str
    priority:      str
    status:        str
    booking_id:    Optional[UUID]
    assigned_to:   Optional[UUID]
    created_at:    datetime
    updated_at:    datetime
    resolved_at:   Optional[datetime]
    closed_at:     Optional[datetime]
    messages:      List[TicketMessageResponse] = []

    class Config:
        from_attributes = True


class TicketSummaryResponse(BaseModel):
    """Compact ticket row for list views — no messages."""
    id:            UUID
    ticket_number: str
    category:      str
    subject:       str
    priority:      str
    status:        str
    booking_id:    Optional[UUID]
    assigned_to:   Optional[UUID]
    created_at:    datetime
    updated_at:    datetime
    resolved_at:   Optional[datetime]

    class Config:
        from_attributes = True


class TicketListResponse(BaseModel):
    """Paginated list of tickets."""
    tickets:  List[TicketSummaryResponse]
    total:    int
    page:     int
    per_page: int
