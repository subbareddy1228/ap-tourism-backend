"""
repositories/support_repo.py
DB access for SupportTicket and TicketMessage models.
"""

from typing import Optional, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.models.support import SupportTicket, TicketMessage


async def get_ticket_by_id(ticket_id: UUID, db: AsyncSession) -> Optional[SupportTicket]:
    """Fetch a support ticket by ID."""
    result = await db.execute(
        select(SupportTicket).where(SupportTicket.id == ticket_id)
    )
    return result.scalar_one_or_none()


async def get_user_tickets(
    user_id: UUID, db: AsyncSession, page: int = 1, per_page: int = 10
) -> dict:
    """Paginated list of all tickets for a user."""
    query = select(SupportTicket).where(SupportTicket.user_id == user_id)
    total = await db.scalar(
        select(func.count()).select_from(query.subquery())
    )
    result = await db.execute(
        query.order_by(SupportTicket.created_at.desc())
             .offset((page - 1) * per_page)
             .limit(per_page)
    )
    return {
        "tickets": result.scalars().all(),
        "total": total or 0,
        "page": page,
        "per_page": per_page,
    }


async def get_all_tickets(
    db: AsyncSession,
    status: Optional[str] = None,
    page: int = 1,
    per_page: int = 20
) -> dict:
    """Admin: all tickets with optional status filter."""
    query = select(SupportTicket)
    if status:
        query = query.where(SupportTicket.status == status)
    total = await db.scalar(
        select(func.count()).select_from(query.subquery())
    )
    result = await db.execute(
        query.order_by(SupportTicket.created_at.desc())
             .offset((page - 1) * per_page)
             .limit(per_page)
    )
    return {
        "tickets": result.scalars().all(),
        "total": total or 0,
        "page": page,
        "per_page": per_page,
    }


async def get_ticket_messages(ticket_id: UUID, db: AsyncSession) -> List[TicketMessage]:
    """Get all messages in a ticket thread."""
    result = await db.execute(
        select(TicketMessage)
        .where(TicketMessage.ticket_id == ticket_id)
        .order_by(TicketMessage.created_at.asc())
    )
    return result.scalars().all()