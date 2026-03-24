# app/routers/admin.py
# Module 19 — Admin APIs /api/v1/admin
# All 45 endpoints. No new DB models — reuses models from modules 1–18.

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from datetime import date, datetime

from src.deps.auth import require_admin
from src.deps.db import get_db
from src.common.utils import delete_cache
from src.common.utils import reports as report_service

from src.models.user import User
from src.models.partner import Partner, PartnerDocument, PartnerEarning
from src.models.models import (
    Booking, Payment, Temple, Destination, Package,
 Review, SupportTicket, Coupon, Banner, PlatformSetting, FAQ
)
from src.schemas.schemas import (
    UserUpdateSchema, UserStatusUpdate, UserRoleUpdate, KYCVerifySchema,
    PartnerStatusUpdate, VerifySchema, CommissionSchema,
    BookingStatusUpdate, AssignGuideSchema, AssignDriverSchema,
    TempleCreateSchema, TempleUpdateSchema,
    DestinationCreateSchema, DestinationUpdateSchema,
    PackageCreateSchema, PackageUpdateSchema,
    AssignAgentSchema, FAQCreateSchema, FAQUpdateSchema,
    CouponCreateSchema, CouponUpdateSchema,
    BannerCreateSchema, BannerUpdateSchema, SettingUpdateSchema,
)

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


# ════════════════════════════════════════════════════════
# DASHBOARD
# ════════════════════════════════════════════════════════

@router.get("/dashboard")
def admin_dashboard(
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    today = date.today()

    today_bookings = db.query(func.count(Booking.id)).filter(
        func.date(Booking.created_at) == today
    ).scalar()

    today_revenue = db.query(func.sum(Payment.amount)).filter(
        Payment.status == "SUCCESS",
        func.date(Payment.created_at) == today
    ).scalar()

    active_trips = db.query(func.count(Booking.id)).filter(
        Booking.status == "ACTIVE"
    ).scalar()

    pending_partner_approvals = db.query(func.count(Partner.id)).filter(
        Partner.status == "APPLIED"
    ).scalar()

    open_support_tickets = db.query(func.count(SupportTicket.id)).filter(
        SupportTicket.status == "OPEN"
    ).scalar()

    return {
        "success": True,
        "data": {
            "today_bookings": today_bookings or 0,
            "today_revenue": float(today_revenue or 0),
            "active_trips": active_trips or 0,
            "pending_partner_approvals": pending_partner_approvals or 0,
            "open_support_tickets": open_support_tickets or 0,
        },
        "message": ""
    }


# ════════════════════════════════════════════════════════
# BOOKING MANAGEMENT
# ════════════════════════════════════════════════════════

@router.get("/bookings")
def list_all_bookings(
    status: str = None,
    booking_type: str = None,
    date_from: str = None,
    date_to: str = None,
    page: int = 1,
    limit: int = 20,
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    query = db.query(Booking)
    if status:
        query = query.filter(Booking.status == status)
    if booking_type:
        query = query.filter(Booking.booking_type == booking_type)
    if date_from:
        query = query.filter(Booking.created_at >= date_from)
    if date_to:
        query = query.filter(Booking.created_at <= date_to)

    total = query.count()
    bookings = query.offset((page - 1) * limit).limit(limit).all()

    return {
        "success": True,
        "data": bookings,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit,
        "message": ""
    }


@router.get("/bookings/{id}")
def get_booking(
    id: int,
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    booking = db.query(Booking).filter(Booking.id == id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return {"success": True, "data": booking, "message": ""}


@router.put("/bookings/{id}/status")
def update_booking_status(
    id: int,
    payload: BookingStatusUpdate,
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    booking = db.query(Booking).filter(Booking.id == id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    booking.status = payload.status
    db.commit()
    return {"success": True, "data": {}, "message": f"Booking status updated to {payload.status}"}


@router.put("/bookings/{id}/assign-guide")
def assign_guide(
    id: int,
    payload: AssignGuideSchema,
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    booking = db.query(Booking).filter(Booking.id == id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    booking.guide_id = payload.guide_id
    db.commit()
    return {"success": True, "data": {}, "message": "Guide assigned"}


@router.put("/bookings/{id}/assign-driver")
def assign_driver(
    id: int,
    payload: AssignDriverSchema,
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    booking = db.query(Booking).filter(Booking.id == id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    booking.driver_id = payload.driver_id
    db.commit()
    return {"success": True, "data": {}, "message": "Driver assigned"}


@router.post("/bookings/{id}/refund")
def admin_force_refund(
    id: int,
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin-initiated refund — bypasses standard cancellation policy."""
    booking = db.query(Booking).filter(Booking.id == id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    payment = db.query(Payment).filter(
        Payment.booking_id == id,
        Payment.status == "SUCCESS"
    ).first()
    if not payment:
        raise HTTPException(status_code=404, detail="No successful payment found for this booking")

    # Mark payment as refunded (actual Razorpay refund call would go here)
    payment.status = "REFUNDED"
    booking.status = "CANCELLED"
    db.commit()

    return {"success": True, "data": {}, "message": "Refund initiated successfully"}


# ════════════════════════════════════════════════════════
# USER MANAGEMENT
# ════════════════════════════════════════════════════════

@router.get("/users")
def list_users(
    role: str = None,
    status: str = None,
    kyc_status: str = None,
    page: int = 1,
    limit: int = 20,
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    if status:
        is_active = status == "ACTIVE"
        query = query.filter(User.is_active == is_active)
    if kyc_status:
        query = query.filter(User.kyc_status == kyc_status)

    total = query.count()
    users = query.offset((page - 1) * limit).limit(limit).all()

    return {
        "success": True,
        "data": users,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit,
        "message": ""
    }


@router.get("/users/{id}")
def get_user(
    id: int,
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    bookings = db.query(Booking).filter(Booking.user_id == id).all()

    return {
        "success": True,
        "data": {
            "user": user,
            "bookings": bookings,
        },
        "message": ""
    }


@router.put("/users/{id}")
def update_user(
    id: int,
    payload: UserUpdateSchema,
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return {"success": True, "data": user, "message": "User updated"}


@router.put("/users/{id}/status")
def update_user_status(
    id: int,
    payload: UserStatusUpdate,
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = (payload.status == "ACTIVE")
    db.commit()
    return {"success": True, "data": {}, "message": f"User {payload.status.lower()}"}


@router.put("/users/{id}/role")
def change_user_role(
    id: int,
    payload: UserRoleUpdate,
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = payload.role
    db.commit()
    return {"success": True, "data": {}, "message": f"User role changed to {payload.role}"}


@router.put("/users/{id}/verify-kyc")
def verify_kyc(
    id: int,
    payload: KYCVerifySchema,
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.kyc_status = "APPROVED" if payload.approved else "REJECTED"
    db.commit()
    return {
        "success": True,
        "data": {},
        "message": f"KYC {'approved' if payload.approved else 'rejected'}"
    }


# ════════════════════════════════════════════════════════
# PARTNER MANAGEMENT
# ════════════════════════════════════════════════════════

@router.get("/partners")
def list_partners(
    verification_status: str = None,
    type: str = None,
    page: int = 1,
    limit: int = 20,
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    query = db.query(Partner)
    if verification_status:
        query = query.filter(Partner.verification_status == verification_status)
    if type:
        query = query.filter(Partner.type == type)

    total = query.count()
    partners = query.offset((page - 1) * limit).limit(limit).all()

    return {
        "success": True,
        "data": partners,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit,
        "message": ""
    }


@router.get("/partners/{id}")
def get_partner(
    id: int,
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    partner = db.query(Partner).filter(Partner.id == id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")

    documents = db.query(PartnerDocument).filter(PartnerDocument.partner_id == id).all()
    total_earnings = db.query(func.sum(PartnerEarning.amount)).filter(
        PartnerEarning.partner_id == id
    ).scalar()

    return {
        "success": True,
        "data": {
            "partner": partner,
            "documents": documents,
            "total_earnings": float(total_earnings or 0),
        },
        "message": ""
    }


@router.put("/partners/{id}/verify")
def verify_partner(
    id: int,
    payload: VerifySchema,
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    partner = db.query(Partner).filter(Partner.id == id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    partner.verification_status = "APPROVED" if payload.approved else "REJECTED"
    if payload.approved:
        partner.status = "ACTIVE"
    db.commit()
    return {
        "success": True,
        "data": {},
        "message": f"Partner {'approved' if payload.approved else 'rejected'}"
    }


@router.put("/partners/{id}/status")
def update_partner_status(
    id: int,
    payload: PartnerStatusUpdate,
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    partner = db.query(Partner).filter(Partner.id == id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    partner.status = payload.status
    partner.is_active = (payload.status == "ACTIVE")
    db.commit()
    return {"success": True, "data": {}, "message": f"Partner {payload.status.lower()}"}


@router.put("/partners/{id}/commission")
def set_commission(
    id: int,
    payload: CommissionSchema,
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    partner = db.query(Partner).filter(Partner.id == id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    partner.commission_rate = payload.rate
    db.commit()
    return {"success": True, "data": {}, "message": f"Commission rate set to {payload.rate}%"}


@router.post("/partners/{id}/payout")
def process_payout(
    id: int,
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    partner = db.query(Partner).filter(Partner.id == id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")

    pending = db.query(func.sum(PartnerEarning.amount)).filter(
        PartnerEarning.partner_id == id,
        PartnerEarning.status == "PENDING"
    ).scalar() or 0

    if pending <= 0:
        raise HTTPException(status_code=400, detail="No pending earnings to pay out")

    # Mark all pending earnings as TRANSFERRED
    db.query(PartnerEarning).filter(
        PartnerEarning.partner_id == id,
        PartnerEarning.status == "PENDING"
    ).update({"status": "TRANSFERRED"})
    db.commit()

    return {
        "success": True,
        "data": {"amount_paid": float(pending)},
        "message": f"Payout of ₹{pending} processed"
    }


# ════════════════════════════════════════════════════════
# REPORTS & ANALYTICS
# ════════════════════════════════════════════════════════

@router.get("/reports/bookings")
def booking_report(
    date_from: str = None,
    date_to: str = None,
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    query = db.query(
        Booking.id,
        Booking.booking_type,
        Booking.status,
        Booking.total_amount,
        Booking.travel_date,
        Booking.created_at
    )
    if date_from:
        query = query.filter(Booking.created_at >= date_from)
    if date_to:
        query = query.filter(Booking.created_at <= date_to)

    rows = query.all()
    data = [{
        "booking_id": r.id,
        "type": r.booking_type,
        "status": r.status,
        "amount": float(r.total_amount or 0),
        "travel_date": str(r.travel_date),
        "created_at": str(r.created_at),
    } for r in rows]

    return report_service.to_csv_response(data, filename="bookings_report.csv")


@router.get("/reports/revenue")
def revenue_report(
    date_from: str = None,
    date_to: str = None,
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    query = db.query(
        func.date(Payment.created_at).label("date"),
        func.count(Payment.id).label("transactions"),
        func.sum(Payment.amount).label("gross_revenue"),
        # GST 18% breakdown
        (func.sum(Payment.amount) * 0.18 / 1.18).label("gst_amount"),
        (func.sum(Payment.amount) / 1.18).label("net_revenue"),
    ).filter(Payment.status == "SUCCESS")

    if date_from:
        query = query.filter(Payment.created_at >= date_from)
    if date_to:
        query = query.filter(Payment.created_at <= date_to)

    rows = query.group_by(func.date(Payment.created_at)).order_by(
        func.date(Payment.created_at)
    ).all()

    data = [{
        "date": str(r.date),
        "transactions": r.transactions,
        "gross_revenue": round(float(r.gross_revenue or 0), 2),
        "gst_amount": round(float(r.gst_amount or 0), 2),
        "net_revenue": round(float(r.net_revenue or 0), 2),
    } for r in rows]

    return report_service.to_csv_response(data, filename="revenue_report.csv")


@router.get("/reports/users")
def user_growth_report(
    date_from: str = None,
    date_to: str = None,
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    query = db.query(
        func.date(User.created_at).label("date"),
        func.count(User.id).label("new_users"),
        func.sum(
            case((User.is_verified == True, 1), else_=0)
        ).label("verified_users")
    )
    if date_from:
        query = query.filter(User.created_at >= date_from)
    if date_to:
        query = query.filter(User.created_at <= date_to)

    rows = query.group_by(func.date(User.created_at)).order_by(
        func.date(User.created_at)
    ).all()

    data = [{
        "date": str(r.date),
        "new_users": r.new_users,
        "verified_users": r.verified_users or 0,
    } for r in rows]

    return report_service.to_csv_response(data, filename="user_growth_report.csv")


@router.get("/reports/partners")
def partner_performance_report(
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    rows = db.query(
        Partner.id,
        Partner.business_name,
        Partner.type,
        func.count(Booking.id).label("total_bookings"),
        func.sum(Payment.amount).label("total_revenue"),
        func.avg(Review.rating).label("avg_rating")
    ).outerjoin(Booking, Booking.partner_id == Partner.id
    ).outerjoin(Payment, Payment.booking_id == Booking.id
    ).outerjoin(Review, Review.entity_id == Partner.id
    ).group_by(Partner.id, Partner.business_name, Partner.type).all()

    data = [{
        "partner_id": r.id,
        "business_name": r.business_name,
        "type": r.type,
        "total_bookings": r.total_bookings or 0,
        "total_revenue": round(float(r.total_revenue or 0), 2),
        "avg_rating": round(float(r.avg_rating or 0), 2),
    } for r in rows]

    return report_service.to_csv_response(data, filename="partner_performance_report.csv")


@router.get("/analytics/overview")
def analytics_overview(
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    today = date.today()
    this_month_start = today.replace(day=1)

    total_users = db.query(func.count(User.id)).scalar()
    total_bookings = db.query(func.count(Booking.id)).scalar()
    total_revenue = db.query(func.sum(Payment.amount)).filter(
        Payment.status == "SUCCESS"
    ).scalar()
    monthly_revenue = db.query(func.sum(Payment.amount)).filter(
        Payment.status == "SUCCESS",
        Payment.created_at >= this_month_start
    ).scalar()
    active_partners = db.query(func.count(Partner.id)).filter(
        Partner.status == "ACTIVE"
    ).scalar()
    avg_booking_value = db.query(func.avg(Payment.amount)).filter(
        Payment.status == "SUCCESS"
    ).scalar()

    top_destinations = db.query(
        Destination.name,
        func.count(Booking.id).label("booking_count")
    ).join(Booking, Booking.destination_id == Destination.id
    ).group_by(Destination.name
    ).order_by(func.count(Booking.id).desc()
    ).limit(5).all()

    return {
        "success": True,
        "data": {
            "total_users": total_users or 0,
            "total_bookings": total_bookings or 0,
            "total_revenue": round(float(total_revenue or 0), 2),
            "monthly_revenue": round(float(monthly_revenue or 0), 2),
            "active_partners": active_partners or 0,
            "avg_booking_value": round(float(avg_booking_value or 0), 2),
            "top_destinations": [
                {"name": d.name, "bookings": d.booking_count}
                for d in top_destinations
            ]
        },
        "message": ""
    }


# ════════════════════════════════════════════════════════
# CONTENT MANAGEMENT — Temples
# ════════════════════════════════════════════════════════

@router.post("/temples")
def add_temple(
    payload: TempleCreateSchema,
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    temple = Temple(**payload.dict())
    db.add(temple)
    db.commit()
    db.refresh(temple)
    return {"success": True, "data": temple, "message": "Temple added"}


@router.put("/temples/{id}")
def update_temple(
    id: int,
    payload: TempleUpdateSchema,
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    temple = db.query(Temple).filter(Temple.id == id).first()
    if not temple:
        raise HTTPException(status_code=404, detail="Temple not found")
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(temple, field, value)
    db.commit()
    db.refresh(temple)
    return {"success": True, "data": temple, "message": "Temple updated"}


@router.delete("/temples/{id}")
def delete_temple(
    id: int,
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    temple = db.query(Temple).filter(Temple.id == id).first()
    if not temple:
        raise HTTPException(status_code=404, detail="Temple not found")
    temple.is_active = False   # soft delete — never hard delete
    db.commit()
    return {"success": True, "data": {}, "message": "Temple removed from platform"}


# ════════════════════════════════════════════════════════
# CONTENT MANAGEMENT — Destinations
# ════════════════════════════════════════════════════════

@router.post("/destinations")
def add_destination(
    payload: DestinationCreateSchema,
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    destination = Destination(**payload.dict())
    db.add(destination)
    db.commit()
    db.refresh(destination)
    return {"success": True, "data": destination, "message": "Destination added"}


@router.put("/destinations/{id}")
def update_destination(
    id: int,
    payload: DestinationUpdateSchema,
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    destination = db.query(Destination).filter(Destination.id == id).first()
    if not destination:
        raise HTTPException(status_code=404, detail="Destination not found")
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(destination, field, value)
    db.commit()
    db.refresh(destination)
    return {"success": True, "data": destination, "message": "Destination updated"}


# ════════════════════════════════════════════════════════
# CONTENT MANAGEMENT — Packages
# ════════════════════════════════════════════════════════

@router.post("/packages")
def create_package(
    payload: PackageCreateSchema,
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    package = Package(**payload.dict())
    db.add(package)
    db.commit()
    db.refresh(package)
    return {"success": True, "data": package, "message": "Package created"}


@router.put("/packages/{id}")
def update_package(
    id: int,
    payload: PackageUpdateSchema,
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    package = db.query(Package).filter(Package.id == id).first()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(package, field, value)
    db.commit()
    db.refresh(package)
    return {"success": True, "data": package, "message": "Package updated"}


# ════════════════════════════════════════════════════════
# SUPPORT MANAGEMENT
# ════════════════════════════════════════════════════════

@router.get("/support/tickets")
def all_tickets(
    status: str = None,
    page: int = 1,
    limit: int = 20,
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    query = db.query(SupportTicket)
    if status:
        query = query.filter(SupportTicket.status == status)

    total = query.count()
    tickets = query.order_by(SupportTicket.created_at.desc()).offset(
        (page - 1) * limit
    ).limit(limit).all()

    return {
        "success": True,
        "data": tickets,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit,
        "message": ""
    }


@router.put("/support/tickets/{id}/assign")
def assign_ticket(
    id: int,
    payload: AssignAgentSchema,
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    ticket = db.query(SupportTicket).filter(SupportTicket.id == id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket.assigned_to = payload.agent_id
    ticket.status = "IN_PROGRESS"
    db.commit()
    return {"success": True, "data": {}, "message": "Ticket assigned to agent"}


@router.put("/support/tickets/{id}/resolve")
def resolve_ticket(
    id: int,
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    ticket = db.query(SupportTicket).filter(SupportTicket.id == id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket.status = "RESOLVED"
    ticket.resolved_at = datetime.utcnow()
    db.commit()
    return {"success": True, "data": {}, "message": "Ticket resolved"}


# ════════════════════════════════════════════════════════
# FAQ MANAGEMENT
# ════════════════════════════════════════════════════════

@router.post("/faqs")
def create_faq(
    payload: FAQCreateSchema,
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    faq = FAQ(**payload.dict())
    db.add(faq)
    db.commit()
    db.refresh(faq)
    return {"success": True, "data": faq, "message": "FAQ created"}


@router.put("/faqs/{id}")
def update_faq(
    id: int,
    payload: FAQUpdateSchema,
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    faq = db.query(FAQ).filter(FAQ.id == id).first()
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ not found")
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(faq, field, value)
    db.commit()
    db.refresh(faq)
    return {"success": True, "data": faq, "message": "FAQ updated"}


# ════════════════════════════════════════════════════════
# COUPON MANAGEMENT
# ════════════════════════════════════════════════════════

@router.get("/coupons")
def list_coupons(
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    coupons = db.query(Coupon).order_by(Coupon.created_at.desc()).all()
    return {"success": True, "data": coupons, "message": ""}


@router.post("/coupons")
def create_coupon(
    payload: CouponCreateSchema,
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    existing = db.query(Coupon).filter(Coupon.code == payload.code).first()
    if existing:
        raise HTTPException(status_code=409, detail="Coupon code already exists")
    coupon = Coupon(**payload.dict())
    db.add(coupon)
    db.commit()
    db.refresh(coupon)
    return {"success": True, "data": coupon, "message": "Coupon created"}


@router.put("/coupons/{id}")
def update_coupon(
    id: int,
    payload: CouponUpdateSchema,
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    coupon = db.query(Coupon).filter(Coupon.id == id).first()
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found")
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(coupon, field, value)
    db.commit()
    db.refresh(coupon)
    return {"success": True, "data": coupon, "message": "Coupon updated"}


@router.delete("/coupons/{id}")
def delete_or_expire_coupon(
    id: int,
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    coupon = db.query(Coupon).filter(Coupon.id == id).first()
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found")
    # Soft expire — preserves history on existing bookings
    coupon.is_active = False
    coupon.expires_at = datetime.utcnow()
    db.commit()
    return {"success": True, "data": {}, "message": "Coupon expired and deactivated"}


# ════════════════════════════════════════════════════════
# BANNER MANAGEMENT
# ════════════════════════════════════════════════════════

@router.get("/banners")
def admin_list_banners(
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    banners = db.query(Banner).order_by(Banner.created_at.desc()).all()
    return {"success": True, "data": banners, "message": ""}


@router.post("/banners")
def create_banner(
    payload: BannerCreateSchema,
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    banner = Banner(**payload.dict())
    db.add(banner)
    db.commit()
    db.refresh(banner)
    delete_cache("public:banners")   # invalidate public cache
    return {"success": True, "data": banner, "message": "Banner created"}


@router.put("/banners/{id}")
def update_banner(
    id: int,
    payload: BannerUpdateSchema,
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    banner = db.query(Banner).filter(Banner.id == id).first()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(banner, field, value)
    db.commit()
    db.refresh(banner)
    delete_cache("public:banners")   # invalidate public cache
    return {"success": True, "data": banner, "message": "Banner updated"}


# ════════════════════════════════════════════════════════
# PLATFORM SETTINGS
# ════════════════════════════════════════════════════════

@router.get("/settings")
def get_settings(
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    settings = db.query(PlatformSetting).all()
    data = {s.key: s.value for s in settings}
    return {"success": True, "data": data, "message": ""}


@router.put("/settings/{key}")
def update_setting(
    key: str,
    payload: SettingUpdateSchema,
    # admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    setting = db.query(PlatformSetting).filter(PlatformSetting.key == key).first()
    if not setting:
        # Create if not exists
        setting = PlatformSetting(key=key, value=payload.value)
        db.add(setting)
    else:
        setting.value = payload.value
    db.commit()
    return {"success": True, "data": {}, "message": f"Setting '{key}' updated"}
