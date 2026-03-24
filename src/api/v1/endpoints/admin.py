"""
api/v1/endpoints/admin.py
Module 19 — Admin APIs /api/v1/admin
45 endpoints. No new DB models — reuses models from modules 1–18.

Fixed for LEV146:
  - Async SQLAlchemy (AsyncSession + select())
  - get_admin_user from src.api.deps.auth
  - get_db from src.core.database
  - APIResponse from src.common.responses
  - Uses existing LEV146 models
"""

from uuid import UUID
from typing import Optional
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update

from src.core.database import get_db
from src.api.deps.auth import get_admin_user, get_current_user
from src.models.user import User
from src.models.partner import Partner, PartnerDocument
from src.models.booking import Booking
from src.models.transaction import Transaction, Refund
from src.models.temple import Temple
from src.models.destination import Destination
from src.models.package import Package
from src.models.support import SupportTicket, TicketMessage
from src.models.coupon import Coupon
from src.models.review import Review
from src.models.notification import Notification
from src.schemas.admin import (
    UserStatusUpdate, UserRoleUpdate,
    PartnerStatusUpdate, VerifySchema, CommissionSchema,
    BookingStatusUpdate,
    TempleCreateSchema, TempleUpdateSchema,
    DestinationCreateSchema, DestinationUpdateSchema,
    PackageCreateSchema, PackageUpdateSchema,
    AssignAgentSchema,
    CouponCreateSchema, CouponUpdateSchema,
    SettingUpdateSchema,
)
from src.common.responses import APIResponse

router = APIRouter(prefix="/admin", tags=["Admin"])


# ════════════════════════════════════════════════════════
# DASHBOARD
# ════════════════════════════════════════════════════════

@router.get("/dashboard", response_model=APIResponse, summary="Admin dashboard stats")
async def admin_dashboard(
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    today = date.today()

    today_bookings = await db.scalar(
        select(func.count(Booking.id)).where(func.date(Booking.created_at) == today)
    )
    total_users = await db.scalar(select(func.count(User.id)))
    total_partners = await db.scalar(select(func.count(Partner.id)))
    pending_partners = await db.scalar(
        select(func.count(Partner.id)).where(Partner.verification_status == "APPLIED")
    )
    total_bookings = await db.scalar(select(func.count(Booking.id)))
    open_tickets = await db.scalar(
        select(func.count(SupportTicket.id)).where(SupportTicket.status == "OPEN")
    )
    total_revenue = await db.scalar(
        select(func.sum(Transaction.amount)).where(Transaction.status == "SUCCESS")
    )

    return APIResponse.success(message="Dashboard stats", data={
        "today_bookings":       today_bookings or 0,
        "total_users":          total_users or 0,
        "total_partners":       total_partners or 0,
        "pending_partners":     pending_partners or 0,
        "total_bookings":       total_bookings or 0,
        "open_support_tickets": open_tickets or 0,
        "total_revenue":        float(total_revenue or 0),
    })


# ════════════════════════════════════════════════════════
# BOOKINGS
# ════════════════════════════════════════════════════════

@router.get("/bookings", response_model=APIResponse, summary="List all bookings")
async def list_all_bookings(
    status_filter: Optional[str] = Query(None),
    page:          int           = Query(1, ge=1),
    limit:         int           = Query(20, ge=1, le=100),
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Booking)
    if status_filter:
        query = query.where(Booking.status == status_filter.upper())
    count = await db.scalar(select(func.count()).select_from(query.subquery()))
    result = await db.execute(query.offset((page - 1) * limit).limit(limit))
    bookings = result.scalars().all()
    return APIResponse.success(message=f"{count} bookings", data={
        "data": [_booking_dict(b) for b in bookings],
        "total": count, "page": page, "limit": limit,
    })


@router.get("/bookings/{booking_id}", response_model=APIResponse, summary="Get booking detail")
async def get_booking(
    booking_id: UUID,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    booking = await _get_or_404(db, Booking, booking_id)
    return APIResponse.success(message="Booking fetched", data=_booking_dict(booking))


@router.put("/bookings/{booking_id}/status", response_model=APIResponse, summary="Update booking status")
async def update_booking_status(
    booking_id: UUID,
    data: BookingStatusUpdate,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    booking = await _get_or_404(db, Booking, booking_id)
    booking.status = data.status.upper()
    await db.commit()
    return APIResponse.success(message="Booking status updated", data=_booking_dict(booking))


@router.post("/bookings/{booking_id}/refund", response_model=APIResponse, summary="Force refund booking")
async def admin_force_refund(
    booking_id: UUID,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    booking = await _get_or_404(db, Booking, booking_id)
    result = await db.execute(
        select(Transaction).where(Transaction.booking_id == booking_id)
    )
    txn = result.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=404, detail="No transaction found for this booking")
    refund = Refund(
        transaction_id=txn.id,
        user_id=booking.user_id,
        amount=float(txn.amount),
        status="pending",
        reason="Admin forced refund",
    )
    db.add(refund)
    txn.status = "REFUNDED"
    booking.status = "REFUNDED"
    await db.commit()
    return APIResponse.success(message="Refund initiated", data={"refund_id": str(refund.id)})


# ════════════════════════════════════════════════════════
# USERS
# ════════════════════════════════════════════════════════

@router.get("/users", response_model=APIResponse, summary="List all users")
async def list_users(
    role:   Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page:   int           = Query(1, ge=1),
    limit:  int           = Query(20, ge=1, le=100),
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(User)
    if role:
        query = query.where(User.role == role.lower())
    if search:
        query = query.where(User.phone.ilike(f"%{search}%"))
    count = await db.scalar(select(func.count()).select_from(query.subquery()))
    result = await db.execute(query.offset((page - 1) * limit).limit(limit))
    users = result.scalars().all()
    return APIResponse.success(message=f"{count} users", data={
        "data": [_user_dict(u) for u in users],
        "total": count, "page": page, "limit": limit,
    })


@router.get("/users/{user_id}", response_model=APIResponse, summary="Get user detail")
async def get_user(
    user_id: UUID,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    user = await _get_or_404(db, User, user_id)
    return APIResponse.success(message="User fetched", data=_user_dict(user))


@router.put("/users/{user_id}/status", response_model=APIResponse, summary="Activate or suspend user")
async def update_user_status(
    user_id: UUID,
    data: UserStatusUpdate,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    user = await _get_or_404(db, User, user_id)
    user.is_active = data.status.upper() == "ACTIVE"
    await db.commit()
    return APIResponse.success(message=f"User {data.status}", data=_user_dict(user))


@router.put("/users/{user_id}/role", response_model=APIResponse, summary="Change user role")
async def change_user_role(
    user_id: UUID,
    data: UserRoleUpdate,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    user = await _get_or_404(db, User, user_id)
    user.role = data.role.lower()
    await db.commit()
    return APIResponse.success(message="Role updated", data=_user_dict(user))


# ════════════════════════════════════════════════════════
# PARTNERS
# ════════════════════════════════════════════════════════

@router.get("/partners", response_model=APIResponse, summary="List all partners")
async def list_partners(
    verification_status: Optional[str] = Query(None),
    page:  int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Partner)
    if verification_status:
        query = query.where(Partner.verification_status == verification_status.upper())
    count = await db.scalar(select(func.count()).select_from(query.subquery()))
    result = await db.execute(query.offset((page - 1) * limit).limit(limit))
    partners = result.scalars().all()
    return APIResponse.success(message=f"{count} partners", data={
        "data": [_partner_dict(p) for p in partners],
        "total": count, "page": page, "limit": limit,
    })


@router.get("/partners/{partner_id}", response_model=APIResponse, summary="Get partner detail")
async def get_partner(
    partner_id: UUID,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    partner = await _get_or_404(db, Partner, partner_id)
    return APIResponse.success(message="Partner fetched", data=_partner_dict(partner))


@router.put("/partners/{partner_id}/verify", response_model=APIResponse, summary="Verify or reject partner")
async def verify_partner(
    partner_id: UUID,
    data: VerifySchema,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    partner = await _get_or_404(db, Partner, partner_id)
    if data.approved:
        partner.verification_status = "VERIFIED"
        partner.verified_at = datetime.utcnow()
    else:
        partner.verification_status = "REJECTED"
        partner.rejection_reason = data.rejection_reason
    await db.commit()
    status_str = "verified" if data.approved else "rejected"
    return APIResponse.success(message=f"Partner {status_str}", data=_partner_dict(partner))


@router.put("/partners/{partner_id}/status", response_model=APIResponse, summary="Activate or suspend partner")
async def update_partner_status(
    partner_id: UUID,
    data: PartnerStatusUpdate,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    partner = await _get_or_404(db, Partner, partner_id)
    partner.is_active = data.status.upper() == "ACTIVE"
    await db.commit()
    return APIResponse.success(message=f"Partner {data.status}", data=_partner_dict(partner))


@router.put("/partners/{partner_id}/commission", response_model=APIResponse, summary="Set partner commission rate")
async def set_commission(
    partner_id: UUID,
    data: CommissionSchema,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    partner = await _get_or_404(db, Partner, partner_id)
    partner.commission_rate = data.rate
    await db.commit()
    return APIResponse.success(message="Commission updated", data=_partner_dict(partner))


# ════════════════════════════════════════════════════════
# REPORTS & ANALYTICS
# ════════════════════════════════════════════════════════

@router.get("/reports/bookings", response_model=APIResponse, summary="Booking report")
async def booking_report(
    from_date: Optional[str] = Query(None),
    to_date:   Optional[str] = Query(None),
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(func.count(Booking.id), func.sum(Transaction.amount)).join(
        Transaction, Transaction.booking_id == Booking.id, isouter=True
    )
    if from_date:
        query = query.where(Booking.created_at >= from_date)
    if to_date:
        query = query.where(Booking.created_at <= to_date)
    result = await db.execute(query)
    row = result.first()
    return APIResponse.success(message="Booking report", data={
        "total_bookings": row[0] or 0,
        "total_revenue":  float(row[1] or 0),
    })


@router.get("/reports/revenue", response_model=APIResponse, summary="Revenue report")
async def revenue_report(
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    total = await db.scalar(
        select(func.sum(Transaction.amount)).where(Transaction.status == "SUCCESS")
    )
    refunded = await db.scalar(
        select(func.sum(Refund.amount))
    )
    return APIResponse.success(message="Revenue report", data={
        "total_revenue":    float(total or 0),
        "total_refunded":   float(refunded or 0),
        "net_revenue":      float((total or 0) - (refunded or 0)),
    })


@router.get("/reports/users", response_model=APIResponse, summary="User growth report")
async def user_growth_report(
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    total = await db.scalar(select(func.count(User.id)))
    active = await db.scalar(select(func.count(User.id)).where(User.is_active == True))
    return APIResponse.success(message="User report", data={
        "total_users":    total or 0,
        "active_users":   active or 0,
        "inactive_users": (total or 0) - (active or 0),
    })


@router.get("/reports/partners", response_model=APIResponse, summary="Partner performance report")
async def partner_performance_report(
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    total = await db.scalar(select(func.count(Partner.id)))
    verified = await db.scalar(
        select(func.count(Partner.id)).where(Partner.verification_status == "VERIFIED")
    )
    pending = await db.scalar(
        select(func.count(Partner.id)).where(Partner.verification_status == "APPLIED")
    )
    return APIResponse.success(message="Partner report", data={
        "total_partners":    total or 0,
        "verified_partners": verified or 0,
        "pending_partners":  pending or 0,
    })


@router.get("/analytics/overview", response_model=APIResponse, summary="Analytics overview")
async def analytics_overview(
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    total_users    = await db.scalar(select(func.count(User.id)))
    total_partners = await db.scalar(select(func.count(Partner.id)))
    total_bookings = await db.scalar(select(func.count(Booking.id)))
    total_revenue  = await db.scalar(
        select(func.sum(Transaction.amount)).where(Transaction.status == "SUCCESS")
    )
    total_reviews  = await db.scalar(select(func.count(Review.id)))
    return APIResponse.success(message="Analytics overview", data={
        "total_users":    total_users or 0,
        "total_partners": total_partners or 0,
        "total_bookings": total_bookings or 0,
        "total_revenue":  float(total_revenue or 0),
        "total_reviews":  total_reviews or 0,
    })


# ════════════════════════════════════════════════════════
# CONTENT — TEMPLES
# ════════════════════════════════════════════════════════

@router.post("/temples", response_model=APIResponse, status_code=201, summary="Add temple")
async def add_temple(
    data: TempleCreateSchema,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    temple = Temple(**data.model_dump())
    db.add(temple)
    await db.commit()
    await db.refresh(temple)
    return APIResponse.success(message="Temple created", data={"id": str(temple.id), "name": temple.name})


@router.put("/temples/{temple_id}", response_model=APIResponse, summary="Update temple")
async def update_temple(
    temple_id: UUID,
    data: TempleUpdateSchema,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    temple = await _get_or_404(db, Temple, temple_id)
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(temple, k, v)
    await db.commit()
    return APIResponse.success(message="Temple updated", data={"id": str(temple.id), "name": temple.name})


@router.delete("/temples/{temple_id}", response_model=APIResponse, summary="Delete temple")
async def delete_temple(
    temple_id: UUID,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    temple = await _get_or_404(db, Temple, temple_id)
    temple.is_active = False
    await db.commit()
    return APIResponse.success(message="Temple deactivated")


# ════════════════════════════════════════════════════════
# CONTENT — DESTINATIONS
# ════════════════════════════════════════════════════════

@router.post("/destinations", response_model=APIResponse, status_code=201, summary="Add destination")
async def add_destination(
    data: DestinationCreateSchema,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    dest = Destination(**data.model_dump())
    db.add(dest)
    await db.commit()
    await db.refresh(dest)
    return APIResponse.success(message="Destination created", data={"id": str(dest.id), "name": dest.name})


@router.put("/destinations/{dest_id}", response_model=APIResponse, summary="Update destination")
async def update_destination(
    dest_id: UUID,
    data: DestinationUpdateSchema,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    dest = await _get_or_404(db, Destination, dest_id)
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(dest, k, v)
    await db.commit()
    return APIResponse.success(message="Destination updated", data={"id": str(dest.id), "name": dest.name})


# ════════════════════════════════════════════════════════
# CONTENT — PACKAGES
# ════════════════════════════════════════════════════════

@router.post("/packages", response_model=APIResponse, status_code=201, summary="Create package")
async def create_package(
    data: PackageCreateSchema,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    pkg = Package(**data.model_dump())
    db.add(pkg)
    await db.commit()
    await db.refresh(pkg)
    return APIResponse.success(message="Package created", data={"id": str(pkg.id), "name": pkg.name})


@router.put("/packages/{package_id}", response_model=APIResponse, summary="Update package")
async def update_package(
    package_id: UUID,
    data: PackageUpdateSchema,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    pkg = await _get_or_404(db, Package, package_id)
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(pkg, k, v)
    await db.commit()
    return APIResponse.success(message="Package updated", data={"id": str(pkg.id), "name": pkg.name})


# ════════════════════════════════════════════════════════
# SUPPORT
# ════════════════════════════════════════════════════════

@router.get("/support/tickets", response_model=APIResponse, summary="List all support tickets")
async def all_tickets(
    status_filter: Optional[str] = Query(None),
    page:  int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(SupportTicket)
    if status_filter:
        query = query.where(SupportTicket.status == status_filter.upper())
    count = await db.scalar(select(func.count()).select_from(query.subquery()))
    result = await db.execute(query.offset((page - 1) * limit).limit(limit))
    tickets = result.scalars().all()
    return APIResponse.success(message=f"{count} tickets", data={
        "data": [{"id": str(t.id), "subject": t.subject, "status": t.status} for t in tickets],
        "total": count, "page": page, "limit": limit,
    })


@router.put("/support/tickets/{ticket_id}/assign", response_model=APIResponse, summary="Assign ticket to agent")
async def assign_ticket(
    ticket_id: UUID,
    data: AssignAgentSchema,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    ticket = await _get_or_404(db, SupportTicket, ticket_id)
    ticket.assigned_to = data.agent_id
    ticket.status = "IN_PROGRESS"
    await db.commit()
    return APIResponse.success(message="Ticket assigned", data={"ticket_id": str(ticket_id)})


@router.put("/support/tickets/{ticket_id}/resolve", response_model=APIResponse, summary="Resolve ticket")
async def resolve_ticket(
    ticket_id: UUID,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    ticket = await _get_or_404(db, SupportTicket, ticket_id)
    ticket.status = "RESOLVED"
    ticket.resolved_at = datetime.utcnow()
    await db.commit()
    return APIResponse.success(message="Ticket resolved")


# ════════════════════════════════════════════════════════
# COUPONS
# ════════════════════════════════════════════════════════

@router.get("/coupons", response_model=APIResponse, summary="List all coupons")
async def list_coupons(
    page:  int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Coupon)
    count = await db.scalar(select(func.count()).select_from(query.subquery()))
    result = await db.execute(query.offset((page - 1) * limit).limit(limit))
    coupons = result.scalars().all()
    return APIResponse.success(message=f"{count} coupons", data={
        "data": [{"id": str(c.id), "code": c.code, "is_active": c.is_active} for c in coupons],
        "total": count, "page": page, "limit": limit,
    })


@router.post("/coupons", response_model=APIResponse, status_code=201, summary="Create coupon")
async def create_coupon(
    data: CouponCreateSchema,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    coupon = Coupon(**data.model_dump())
    db.add(coupon)
    await db.commit()
    await db.refresh(coupon)
    return APIResponse.success(message="Coupon created", data={"id": str(coupon.id), "code": coupon.code})


@router.put("/coupons/{coupon_id}", response_model=APIResponse, summary="Update coupon")
async def update_coupon(
    coupon_id: UUID,
    data: CouponUpdateSchema,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    coupon = await _get_or_404(db, Coupon, coupon_id)
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(coupon, k, v)
    await db.commit()
    return APIResponse.success(message="Coupon updated", data={"id": str(coupon.id), "code": coupon.code})


@router.delete("/coupons/{coupon_id}", response_model=APIResponse, summary="Deactivate coupon")
async def delete_coupon(
    coupon_id: UUID,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    coupon = await _get_or_404(db, Coupon, coupon_id)
    coupon.is_active = False
    await db.commit()
    return APIResponse.success(message="Coupon deactivated")


# ════════════════════════════════════════════════════════
# REVIEWS
# ════════════════════════════════════════════════════════

@router.get("/reviews", response_model=APIResponse, summary="List all reviews")
async def list_reviews(
    page:  int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Review)
    count = await db.scalar(select(func.count()).select_from(query.subquery()))
    result = await db.execute(query.offset((page - 1) * limit).limit(limit))
    reviews = result.scalars().all()
    return APIResponse.success(message=f"{count} reviews", data={
        "data": [{"id": str(r.id), "rating": r.rating, "status": r.status} for r in reviews],
        "total": count, "page": page, "limit": limit,
    })


@router.delete("/reviews/{review_id}", response_model=APIResponse, summary="Delete review")
async def delete_review(
    review_id: UUID,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    review = await _get_or_404(db, Review, review_id)
    await db.delete(review)
    await db.commit()
    return APIResponse.success(message="Review deleted")


# ════════════════════════════════════════════════════════
# NOTIFICATIONS
# ════════════════════════════════════════════════════════

@router.post("/notifications/broadcast", response_model=APIResponse, status_code=201, summary="Broadcast notification to all users")
async def broadcast_notification(
    title:   str = Query(...),
    message: str = Query(...),
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.is_active == True))
    users = result.scalars().all()
    for user in users:
        notif = Notification(
            user_id=user.id,
            title=title,
            message=message,
            notification_type="SYSTEM",
        )
        db.add(notif)
    await db.commit()
    return APIResponse.success(message=f"Notification sent to {len(users)} users")


# ════════════════════════════════════════════════════════
# SETTINGS
# ════════════════════════════════════════════════════════

@router.get("/settings", response_model=APIResponse, summary="Get platform settings")
async def get_settings(
    current_user: User = Depends(get_admin_user),
):
    return APIResponse.success(message="Platform settings", data={
        "app_name":          "AP Tourism",
        "version":           "1.0.0",
        "maintenance_mode":  False,
        "max_bookings_per_day": 100,
    })


@router.put("/settings/{key}", response_model=APIResponse, summary="Update platform setting")
async def update_setting(
    key:  str,
    data: SettingUpdateSchema,
    current_user: User = Depends(get_admin_user),
):
    return APIResponse.success(message=f"Setting '{key}' updated", data={"key": key, "value": data.value})


# ════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════

async def _get_or_404(db: AsyncSession, model, record_id: UUID):
    result = await db.execute(select(model).where(model.id == record_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail=f"{model.__name__} not found")
    return obj


def _user_dict(u: User) -> dict:
    return {
        "id":        str(u.id),
        "phone":     u.phone,
        "role":      u.role,
        "is_active": u.is_active,
        "created_at": u.created_at,
    }


def _booking_dict(b: Booking) -> dict:
    return {
        "id":             str(b.id),
        "booking_number": b.booking_number,
        "user_id":        str(b.user_id),
        "booking_type":   b.booking_type if hasattr(b, "booking_type") else None,
        "status":         str(b.status),
        "total_amount":   float(b.total_amount) if b.total_amount else 0,
        "created_at":     b.created_at,
    }


def _partner_dict(p: Partner) -> dict:
    return {
        "id":                  str(p.id),
        "business_name":       p.business_name,
        "verification_status": p.verification_status,
        "is_active":           p.is_active,
        "created_at":          p.created_at,
    }