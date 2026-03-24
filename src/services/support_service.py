"""
services/support_service.py
Business logic for M17 — Support APIs.
Owner: LEV156 Ram Kishore Pawar

Functions:
    create_ticket          — user opens a new ticket
    list_my_tickets        — user's own ticket list (paginated)
    get_ticket_by_id       — single ticket with messages (ownership enforced)
    add_message            — user or admin adds a reply
    close_ticket           — user closes their own ticket
    reopen_ticket          — user reopens a resolved/closed ticket
    admin_list_all_tickets — admin views all tickets with filters
    admin_assign_ticket    — admin assigns ticket to a handler
    admin_resolve_ticket   — admin marks ticket resolved
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from src.models.support import SupportTicket, TicketMessage
from src.models.user import User
from src.schemas.support import (
    CreateTicketRequest,
    AddMessageRequest,
    AssignTicketRequest,
    ResolveTicketRequest,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# INTERNAL HELPERS
# ═══════════════════════════════════════════════════════════════

def _generate_ticket_number() -> str:
    """
    Generate a human-readable ticket number.
    Format: TKT-YYYYMMDD-<4 random hex chars>
    e.g. TKT-20260324-A3F1
    """
    date_part = datetime.utcnow().strftime("%Y%m%d")
    rand_part = uuid4().hex[:4].upper()
    return f"TKT-{date_part}-{rand_part}"


async def _get_ticket_for_user(
    ticket_id: UUID,
    user_id: UUID,
    db: AsyncSession,
) -> SupportTicket:
    """Fetch ticket by ID, verify it belongs to user. Raise 404 if not found."""
    result = await db.execute(
        select(SupportTicket).where(
            and_(
                SupportTicket.id == ticket_id,
                SupportTicket.user_id == user_id,
            )
        )
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )
    return ticket


async def _get_ticket_for_admin(
    ticket_id: UUID,
    db: AsyncSession,
) -> SupportTicket:
    """Fetch ticket by ID for admin — no ownership filter."""
    result = await db.execute(
        select(SupportTicket).where(SupportTicket.id == ticket_id)
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )
    return ticket


# ═══════════════════════════════════════════════════════════════
# 1. CREATE TICKET
# POST /support/tickets
# ═══════════════════════════════════════════════════════════════

async def create_ticket(
    data: CreateTicketRequest,
    current_user: User,
    db: AsyncSession,
) -> SupportTicket:
    """
    Open a new support ticket.
    The first message is created alongside the ticket in one transaction.
    """
    ticket = SupportTicket(
        user_id       = current_user.id,
        ticket_number = _generate_ticket_number(),
        category      = data.category,
        subject       = data.subject,
        priority      = data.priority,
        status        = "open",
        booking_id    = data.booking_id,
    )
    db.add(ticket)
    await db.flush()    # get ticket.id before creating message

    # First message from the user
    first_message = TicketMessage(
        ticket_id   = ticket.id,
        sender_id   = current_user.id,
        sender_type = "user",
        body        = data.body,
    )
    db.add(first_message)

    await db.commit()
    await db.refresh(ticket)

    logger.info(
        "Support ticket created ticket_number=%s user_id=%s category=%s",
        ticket.ticket_number, current_user.id, data.category,
    )

    return ticket


# ═══════════════════════════════════════════════════════════════
# 2. LIST MY TICKETS
# GET /support/tickets  (user)
# ═══════════════════════════════════════════════════════════════

async def list_my_tickets(
    current_user: User,
    db: AsyncSession,
    page: int = 1,
    per_page: int = 10,
    ticket_status: Optional[str] = None,
    category: Optional[str] = None,
) -> dict:
    """Return paginated list of the current user's tickets, newest first."""
    query = select(SupportTicket).where(
        SupportTicket.user_id == current_user.id
    )

    if ticket_status:
        query = query.where(SupportTicket.status == ticket_status)
    if category:
        query = query.where(SupportTicket.category == category)

    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar()

    query = (
        query
        .order_by(SupportTicket.updated_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )

    result = await db.execute(query)
    tickets = result.scalars().all()

    return {"tickets": tickets, "total": total, "page": page, "per_page": per_page}


# ═══════════════════════════════════════════════════════════════
# 3. GET TICKET BY ID  (user)
# GET /support/tickets/{ticket_id}
# ═══════════════════════════════════════════════════════════════

async def get_ticket_by_id(
    ticket_id: UUID,
    current_user: User,
    db: AsyncSession,
) -> SupportTicket:
    """
    Fetch full ticket detail with messages.
    Messages returned oldest-first (chronological thread order).
    Internal admin notes are hidden from regular users.
    """
    ticket = await _get_ticket_for_user(ticket_id, current_user.id, db)

    # Eagerly load messages, hiding internal notes for non-admin users
    msg_result = await db.execute(
        select(TicketMessage).where(
            and_(
                TicketMessage.ticket_id == ticket.id,
                TicketMessage.is_internal == False,
            )
        ).order_by(TicketMessage.created_at)
    )
    ticket.messages = msg_result.scalars().all()

    return ticket


# ═══════════════════════════════════════════════════════════════
# 4. ADD MESSAGE
# POST /support/tickets/{ticket_id}/messages
# ═══════════════════════════════════════════════════════════════

async def add_message(
    ticket_id: UUID,
    data: AddMessageRequest,
    current_user: User,
    db: AsyncSession,
    is_admin: bool = False,
) -> TicketMessage:
    """
    Add a reply to an existing ticket.
    Users can reply to open / in_progress / reopened tickets.
    Admins can reply to any ticket.
    Replying to a closed ticket raises 400.
    """
    if is_admin:
        ticket = await _get_ticket_for_admin(ticket_id, db)
    else:
        ticket = await _get_ticket_for_user(ticket_id, current_user.id, db)

    if ticket.status == "closed" and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reply to a closed ticket. Please reopen it first.",
        )

    sender_type = "admin" if is_admin else "user"

    message = TicketMessage(
        ticket_id   = ticket.id,
        sender_id   = current_user.id,
        sender_type = sender_type,
        body        = data.body,
        attachments = data.attachments,
        is_internal = data.is_internal if is_admin else False,
    )
    db.add(message)

    # When user replies to a resolved ticket, auto-reopen it
    if not is_admin and ticket.status == "resolved":
        ticket.status     = "reopened"
        ticket.updated_at = datetime.utcnow()

    # When admin replies to open ticket, move to in_progress
    elif is_admin and ticket.status == "open":
        ticket.status     = "in_progress"
        ticket.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(message)

    return message


# ═══════════════════════════════════════════════════════════════
# 5. CLOSE TICKET  (user)
# PUT /support/tickets/{ticket_id}/close
# ═══════════════════════════════════════════════════════════════

async def close_ticket(
    ticket_id: UUID,
    current_user: User,
    db: AsyncSession,
) -> SupportTicket:
    """User closes their own ticket. Only open / in_progress / resolved allowed."""
    ticket = await _get_ticket_for_user(ticket_id, current_user.id, db)

    closeable = {"open", "in_progress", "resolved", "reopened"}
    if ticket.status not in closeable:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ticket is already {ticket.status}",
        )

    ticket.status    = "closed"
    ticket.closed_at = datetime.utcnow()
    ticket.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(ticket)

    logger.info("Ticket closed ticket_id=%s by user_id=%s", ticket_id, current_user.id)

    return ticket


# ═══════════════════════════════════════════════════════════════
# 6. REOPEN TICKET  (user)
# POST /support/tickets/{ticket_id}/reopen
# ═══════════════════════════════════════════════════════════════

async def reopen_ticket(
    ticket_id: UUID,
    current_user: User,
    db: AsyncSession,
) -> SupportTicket:
    """
    User reopens a resolved or closed ticket.
    Only resolved and closed tickets can be reopened.
    """
    ticket = await _get_ticket_for_user(ticket_id, current_user.id, db)

    reopenable = {"resolved", "closed"}
    if ticket.status not in reopenable:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only resolved or closed tickets can be reopened. Current status: {ticket.status}",
        )

    ticket.status      = "reopened"
    ticket.resolved_at = None
    ticket.closed_at   = None
    ticket.updated_at  = datetime.utcnow()

    await db.commit()
    await db.refresh(ticket)

    logger.info("Ticket reopened ticket_id=%s by user_id=%s", ticket_id, current_user.id)

    return ticket


# ═══════════════════════════════════════════════════════════════
# 7. ADMIN — LIST ALL TICKETS
# GET /support/tickets  (admin)
# ═══════════════════════════════════════════════════════════════

async def admin_list_all_tickets(
    db: AsyncSession,
    page: int = 1,
    per_page: int = 20,
    ticket_status: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    assigned_to: Optional[UUID] = None,
) -> dict:
    """Admin view — all tickets across all users with optional filters."""
    query = select(SupportTicket)

    if ticket_status:
        query = query.where(SupportTicket.status == ticket_status)
    if category:
        query = query.where(SupportTicket.category == category)
    if priority:
        query = query.where(SupportTicket.priority == priority)
    if assigned_to:
        query = query.where(SupportTicket.assigned_to == assigned_to)

    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar()

    # Urgent + high first, then newest
    query = (
        query
        .order_by(SupportTicket.updated_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )

    result = await db.execute(query)
    tickets = result.scalars().all()

    return {"tickets": tickets, "total": total, "page": page, "per_page": per_page}


# ═══════════════════════════════════════════════════════════════
# 8. ADMIN — ASSIGN TICKET
# PUT /support/tickets/{ticket_id}/assign
# ═══════════════════════════════════════════════════════════════

async def admin_assign_ticket(
    ticket_id: UUID,
    data: AssignTicketRequest,
    db: AsyncSession,
) -> SupportTicket:
    """Admin assigns the ticket to another admin user."""
    ticket = await _get_ticket_for_admin(ticket_id, db)

    ticket.assigned_to = data.assigned_to
    ticket.status      = "in_progress" if ticket.status == "open" else ticket.status
    ticket.updated_at  = datetime.utcnow()

    await db.commit()
    await db.refresh(ticket)

    logger.info(
        "Ticket assigned ticket_id=%s assigned_to=%s",
        ticket_id, data.assigned_to,
    )

    return ticket


# ═══════════════════════════════════════════════════════════════
# 9. ADMIN — RESOLVE TICKET
# PUT /support/tickets/{ticket_id}/resolve
# ═══════════════════════════════════════════════════════════════

async def admin_resolve_ticket(
    ticket_id: UUID,
    data: ResolveTicketRequest,
    admin: User,
    db: AsyncSession,
) -> SupportTicket:
    """
    Admin marks ticket as resolved.
    Optionally posts a closing message to the thread.
    """
    ticket = await _get_ticket_for_admin(ticket_id, db)

    if ticket.status in {"closed", "resolved"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ticket is already {ticket.status}",
        )

    # Post resolution note as a system message if provided
    if data.resolution_note:
        resolution_message = TicketMessage(
            ticket_id   = ticket.id,
            sender_id   = admin.id,
            sender_type = "admin",
            body        = data.resolution_note,
            is_internal = False,
        )
        db.add(resolution_message)

    ticket.status      = "resolved"
    ticket.resolved_at = datetime.utcnow()
    ticket.updated_at  = datetime.utcnow()

    await db.commit()
    await db.refresh(ticket)

    logger.info(
        "Ticket resolved ticket_id=%s by admin_id=%s",
        ticket_id, admin.id,
    )

    return ticket
