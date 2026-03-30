"""
api/v1/endpoints/support.py
M17 — Support APIs  (12 endpoints)
Owner: LEV156 Ram Kishore Pawar

Routes:
  POST   /support/tickets                        → Create ticket
  GET    /support/tickets                        → My tickets (user) / All tickets (admin)
  GET    /support/tickets/{ticket_id}            → Ticket detail + messages
  POST   /support/tickets/{ticket_id}/messages   → Add reply
  PUT    /support/tickets/{ticket_id}/close      → Close ticket (user)
  POST   /support/tickets/{ticket_id}/reopen     → Reopen ticket (user)
  GET    /support/admin/tickets                  → Admin: all tickets with filters
  PUT    /support/admin/tickets/{ticket_id}/assign   → Admin: assign ticket
  PUT    /support/admin/tickets/{ticket_id}/resolve  → Admin: resolve ticket
  POST   /support/admin/tickets/{ticket_id}/messages → Admin: add reply / internal note
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.api.deps.auth import get_current_user, get_admin_user
from src.models.user import User
from src.schemas.support import (
    CreateTicketRequest,
    AddMessageRequest,
    AssignTicketRequest,
    ResolveTicketRequest,
    TicketResponse,
    TicketSummaryResponse,
    TicketListResponse,
    TicketMessageResponse,
)
from src.common.responses import APIResponse
from src.services import support_service

router = APIRouter(prefix="/support", tags=["Support"])


# ── 1. CREATE TICKET ──────────────────────────────────────────
@router.post(
    "/tickets",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a support ticket",
)
async def create_ticket(
    data: CreateTicketRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession   = Depends(get_db),
):
    """
    Open a new support ticket.

    **Categories:** booking | payment | refund | guide | hotel | vehicle | app | other

    **Priority:** low | medium | high | urgent  (default: medium)

    The `body` field becomes the first message in the ticket thread.
    Optionally attach a `booking_id` to link the ticket to a specific booking.
    """
    ticket = await support_service.create_ticket(data, current_user, db)
    return APIResponse.success(
        message="Support ticket created successfully",
        data=TicketResponse.model_validate(ticket).model_dump(),
    )


# ── 2. LIST MY TICKETS  (user) ────────────────────────────────
@router.get(
    "/tickets",
    response_model=APIResponse,
    summary="List my support tickets",
)
async def list_my_tickets(
    page:     int           = Query(default=1,    ge=1),
    per_page: int           = Query(default=10,   ge=1, le=50),
    status:   Optional[str] = Query(default=None, description="Filter: open | in_progress | resolved | closed | reopened"),
    category: Optional[str] = Query(default=None, description="Filter: booking | payment | refund | guide | hotel | vehicle | app | other"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession   = Depends(get_db),
):
    """
    Get paginated list of tickets raised by the current user.
    Newest / most recently updated tickets appear first.
    """
    result = await support_service.list_my_tickets(
        current_user=current_user,
        db=db,
        page=page,
        per_page=per_page,
        ticket_status=status,
        category=category,
    )
    return APIResponse.success(
        message="Tickets fetched",
        data={
            "tickets":  [TicketSummaryResponse.model_validate(t).model_dump()
                         for t in result["tickets"]],
            "total":    result["total"],
            "page":     result["page"],
            "per_page": result["per_page"],
        },
    )


# ── 3. GET TICKET DETAIL  (user) ──────────────────────────────
@router.get(
    "/tickets/{ticket_id}",
    response_model=APIResponse,
    summary="Get ticket detail with messages",
)
async def get_ticket(
    ticket_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession   = Depends(get_db),
):
    """
    Get full ticket detail including the complete message thread.
    Internal admin notes are hidden from regular users.
    Returns 404 if ticket doesn't exist or belongs to another user.
    """
    ticket = await support_service.get_ticket_by_id(ticket_id, current_user, db)
    return APIResponse.success(
        message="Ticket fetched",
        data=TicketResponse.model_validate(ticket).model_dump(),
    )


# ── 4. ADD MESSAGE  (user) ────────────────────────────────────
@router.post(
    "/tickets/{ticket_id}/messages",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Reply to a support ticket",
)
async def add_message(
    ticket_id: UUID,
    data: AddMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession   = Depends(get_db),
):
    """
    Add a reply to an existing ticket.

    - Replying to a **resolved** ticket automatically reopens it.
    - Replying to a **closed** ticket returns 400 — reopen first.
    - `attachments` should be pre-uploaded S3 URLs.
    """
    message = await support_service.add_message(
        ticket_id=ticket_id,
        data=data,
        current_user=current_user,
        db=db,
        is_admin=False,
    )
    return APIResponse.success(
        message="Message added",
        data=TicketMessageResponse.model_validate(message).model_dump(),
    )


# ── 5. CLOSE TICKET  (user) ───────────────────────────────────
@router.put(
    "/tickets/{ticket_id}/close",
    response_model=APIResponse,
    summary="Close a support ticket",
)
async def close_ticket(
    ticket_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession   = Depends(get_db),
):
    """
    Close a ticket you raised.
    Can be closed from: open, in_progress, resolved, or reopened state.
    Closed tickets can be reopened via POST /tickets/{id}/reopen.
    """
    ticket = await support_service.close_ticket(ticket_id, current_user, db)
    return APIResponse.success(
        message="Ticket closed successfully",
        data=TicketSummaryResponse.model_validate(ticket).model_dump(),
    )


# ── 6. REOPEN TICKET  (user) ──────────────────────────────────
@router.post(
    "/tickets/{ticket_id}/reopen",
    response_model=APIResponse,
    summary="Reopen a resolved or closed ticket",
)
async def reopen_ticket(
    ticket_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession   = Depends(get_db),
):
    """
    Reopen a ticket that was resolved or closed.
    Use this when the issue was not fully fixed.
    """
    ticket = await support_service.reopen_ticket(ticket_id, current_user, db)
    return APIResponse.success(
        message="Ticket reopened",
        data=TicketSummaryResponse.model_validate(ticket).model_dump(),
    )


# ══════════════════════════════════════════════
# ADMIN ROUTES
# ══════════════════════════════════════════════

# ── 7. ADMIN — LIST ALL TICKETS ───────────────────────────────
@router.get(
    "/admin/tickets",
    response_model=APIResponse,
    summary="[Admin] List all tickets",
)
async def admin_list_tickets(
    page:        int           = Query(default=1,    ge=1),
    per_page:    int           = Query(default=20,   ge=1, le=100),
    status:      Optional[str] = Query(default=None),
    category:    Optional[str] = Query(default=None),
    priority:    Optional[str] = Query(default=None, description="low | medium | high | urgent"),
    assigned_to: Optional[UUID] = Query(default=None, description="Filter by assigned admin user_id"),
    admin: User      = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    **Admin only.** View all support tickets across all users.

    **Filters:** status, category, priority, assigned_to (admin user_id)

    Results ordered by most recently updated first.
    """
    result = await support_service.admin_list_all_tickets(
        db=db,
        page=page,
        per_page=per_page,
        ticket_status=status,
        category=category,
        priority=priority,
        assigned_to=assigned_to,
    )
    return APIResponse.success(
        message="All tickets fetched",
        data={
            "tickets":  [TicketSummaryResponse.model_validate(t).model_dump()
                         for t in result["tickets"]],
            "total":    result["total"],
            "page":     result["page"],
            "per_page": result["per_page"],
        },
    )


# ── 8. ADMIN — ASSIGN TICKET ──────────────────────────────────
@router.put(
    "/admin/tickets/{ticket_id}/assign",
    response_model=APIResponse,
    summary="[Admin] Assign ticket to a handler",
)
async def admin_assign_ticket(
    ticket_id: UUID,
    data: AssignTicketRequest,
    admin: User      = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    **Admin only.** Assign a ticket to an admin user.
    If the ticket is still `open`, it moves to `in_progress` automatically.
    """
    ticket = await support_service.admin_assign_ticket(ticket_id, data, db)
    return APIResponse.success(
        message="Ticket assigned successfully",
        data=TicketSummaryResponse.model_validate(ticket).model_dump(),
    )


# ── 9. ADMIN — RESOLVE TICKET ─────────────────────────────────
@router.put(
    "/admin/tickets/{ticket_id}/resolve",
    response_model=APIResponse,
    summary="[Admin] Resolve a ticket",
)
async def admin_resolve_ticket(
    ticket_id: UUID,
    data: ResolveTicketRequest,
    admin: User      = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    **Admin only.** Mark a ticket as resolved.
    Optionally include a `resolution_note` which is posted as the final message to the user.
    """
    ticket = await support_service.admin_resolve_ticket(ticket_id, data, admin, db)
    return APIResponse.success(
        message="Ticket resolved successfully",
        data=TicketSummaryResponse.model_validate(ticket).model_dump(),
    )


# ── 10. ADMIN — ADD MESSAGE / INTERNAL NOTE ───────────────────
@router.post(
    "/admin/tickets/{ticket_id}/messages",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="[Admin] Reply to ticket or add internal note",
)
async def admin_add_message(
    ticket_id: UUID,
    data: AddMessageRequest,
    admin: User      = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    **Admin only.** Add a reply or internal note to any ticket.

    - `is_internal: false` → visible to the user in the thread
    - `is_internal: true`  → internal note, hidden from the user
    """
    message = await support_service.add_message(
        ticket_id=ticket_id,
        data=data,
        current_user=admin,
        db=db,
        is_admin=True,
    )
    return APIResponse.success(
        message="Message added",
        data=TicketMessageResponse.model_validate(message).model_dump(),
    )

@router.get(
    "/admin/tickets/{ticket_id}",
    response_model=APIResponse,
    summary="[Admin] Get ticket detail"
)
async def admin_get_ticket(
    ticket_id: str,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get full detail of any support ticket including all messages."""
    result = await support_service.get_ticket_by_id(ticket_id, db, is_admin=True)
    return APIResponse.success(message="Ticket fetched", data=result)

@router.get(
    "/admin/tickets/{ticket_id}/messages",
    response_model=APIResponse,
    summary="[Admin] Get all messages in a ticket"
)
async def admin_get_ticket_messages(
    ticket_id: str,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all messages in a support ticket thread."""
    result = await support_service.get_ticket_messages(ticket_id, db)
    return APIResponse.success(message="Messages fetched", data=result)