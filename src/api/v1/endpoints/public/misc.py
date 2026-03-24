# app/routers/public.py
# Module 20 — Public/Misc APIs /api/v1/
# 10 endpoints. No auth required. Aggregated homepage + health + static data.

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import redis
import os

from src.api.deps.database import get_db
from src.common.utils import get_cache, set_cache
from src.websockets.notifications import send_email
from src.schemas import ContactUsSchema

from src.models import (
    Destination, Package, Temple, Banner, ContactMessage, FAQ
)

router = APIRouter(prefix="/api/v1", tags=["Public"])

# ─── Static data ────────────────────────────────────────────
AP_DISTRICTS = [
    "Visakhapatnam", "Vizianagaram", "Srikakulam", "East Godavari",
    "West Godavari", "Krishna", "Guntur", "Prakasam", "Nellore",
    "Chittoor", "Kadapa", "Anantapur", "Kurnool", "Tirupati",
    "Palnadu", "Nandyal", "Anakapalli", "Alluri Sitharama Raju",
    "Konaseema", "Bapatla", "Eluru", "NTR District", "Manyam"
]

AP_CITIES = [
    {"city": "Visakhapatnam", "district": "Visakhapatnam"},
    {"city": "Vijayawada", "district": "Krishna"},
    {"city": "Guntur", "district": "Guntur"},
    {"city": "Tirupati", "district": "Tirupati"},
    {"city": "Rajahmundry", "district": "East Godavari"},
    {"city": "Kakinada", "district": "East Godavari"},
    {"city": "Nellore", "district": "Nellore"},
    {"city": "Kurnool", "district": "Kurnool"},
    {"city": "Kadapa", "district": "Kadapa"},
    {"city": "Anantapur", "district": "Anantapur"},
    {"city": "Eluru", "district": "Eluru"},
    {"city": "Ongole", "district": "Prakasam"},
    {"city": "Srikakulam", "district": "Srikakulam"},
    {"city": "Vizianagaram", "district": "Vizianagaram"},
    {"city": "Bhimavaram", "district": "West Godavari"},
]


# ════════════════════════════════════════════════════════
# HEALTH & VERSION
# ════════════════════════════════════════════════════════

@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Load balancer health check. Returns DB and Redis connectivity status."""
    try:
        db.execute("SELECT 1")
        db_ok = True
    except Exception:
        db_ok = False

    try:
        r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
        r.ping()
        redis_ok = True
    except Exception:
        redis_ok = False

    return {
        "success": True,
        "data": {
            "status": "ok",
            "version": os.getenv("APP_VERSION", "1.0.0"),
            "db_connected": db_ok,
            "redis_connected": redis_ok,
        },
        "message": ""
    }


@router.get("/version")
def get_version():
    """Returns current API version, build number, and deployment timestamp."""
    return {
        "success": True,
        "data": {
            "version": os.getenv("APP_VERSION", "1.0.0"),
            "build": os.getenv("BUILD_NUMBER", "local"),
            "deployed_at": os.getenv("DEPLOY_TIMESTAMP", "unknown"),
        },
        "message": ""
    }


# ════════════════════════════════════════════════════════
# CONFIGURATION
# ════════════════════════════════════════════════════════

@router.get("/config")
def get_config():
    """App configuration for clients — payment methods, policies, languages."""
    return {
        "success": True,
        "data": {
            "supported_payment_methods": ["UPI", "CARD", "NET_BANKING", "WALLET", "EMI", "PAY_LATER"],
            "min_booking_advance_hours": 2,
            "cancellation_policy_text": ">48hrs full refund, 24-48hrs 50%, <24hrs no refund",
            "supported_languages": ["Telugu", "Hindi", "English", "Tamil", "Kannada"],
            "currency": "INR",
            "gst_rate": 18,
            "platform_name": "AP Travel & Temple",
            "support_phone": "+91-XXXXXXXXXX",
            "support_email": "support@aptraveltemple.com",
        },
        "message": ""
    }


# ════════════════════════════════════════════════════════
# BANNERS
# ════════════════════════════════════════════════════════

@router.get("/banners")
def get_banners(db: Session = Depends(get_db)):
    """Active homepage banners/promotions. Cached 30 minutes."""
    cached = get_cache("public:banners")
    if cached:
        return {"success": True, "data": cached, "message": ""}

    banners = db.query(Banner).filter(Banner.is_active == True).all()
    result = [
        {"id": b.id, "title": b.title, "image_url": b.image_url, "link": b.link}
        for b in banners
    ]
    set_cache("public:banners", result, ttl=1800)   # 30 min
    return {"success": True, "data": result, "message": ""}


# ════════════════════════════════════════════════════════
# HOMEPAGE AGGREGATED DATA
# ════════════════════════════════════════════════════════

@router.get("/home")
def get_homepage(db: Session = Depends(get_db)):
    """
    Aggregated homepage data — featured destinations, packages,
    popular temples, active banners. Cached 30 minutes.
    """
    cached = get_cache("public:home")
    if cached:
        return {"success": True, "data": cached, "message": ""}

    featured_destinations = db.query(Destination).filter(
        Destination.is_featured == True,
        Destination.is_active == True
    ).limit(6).all()

    featured_packages = db.query(Package).filter(
        Package.is_featured == True,
        Package.is_active == True
    ).limit(6).all()

    popular_temples = db.query(Temple).filter(
        Temple.is_active == True
    ).order_by(Temple.booking_count.desc()).limit(6).all()

    active_banners = db.query(Banner).filter(Banner.is_active == True).all()

    data = {
        "featured_destinations": [
            {"id": d.id, "name": d.name, "type": d.type, "district": d.district}
            for d in featured_destinations
        ],
        "featured_packages": [
            {"id": p.id, "name": p.name, "duration_days": p.duration_days, "price": p.price}
            for p in featured_packages
        ],
        "popular_temples": [
            {"id": t.id, "name": t.name, "deity": t.deity, "district": t.district}
            for t in popular_temples
        ],
        "active_banners": [
            {"id": b.id, "title": b.title, "image_url": b.image_url, "link": b.link}
            for b in active_banners
        ],
    }

    set_cache("public:home", data, ttl=1800)   # 30 min
    return {"success": True, "data": data, "message": ""}


# ════════════════════════════════════════════════════════
# LOCATION DATA
# ════════════════════════════════════════════════════════

@router.get("/districts")
def get_districts():
    """All Andhra Pradesh districts for dropdown filters."""
    return {"success": True, "data": AP_DISTRICTS, "message": ""}


@router.get("/cities")
def get_cities():
    """Cities list with district mapping."""
    return {"success": True, "data": AP_CITIES, "message": ""}


# ════════════════════════════════════════════════════════
# LOCALIZATION
# ════════════════════════════════════════════════════════

@router.get("/languages")
def get_languages():
    """Supported languages on the platform."""
    return {
        "success": True,
        "data": ["Telugu", "Hindi", "English", "Tamil", "Kannada"],
        "message": ""
    }


@router.get("/currencies")
def get_currencies():
    """Supported currencies (currently INR only)."""
    return {"success": True, "data": ["INR"], "message": ""}


# ════════════════════════════════════════════════════════
# CONTACT
# ════════════════════════════════════════════════════════

@router.post("/contact-us")
def contact_us(
    payload: ContactUsSchema,
    db: Session = Depends(get_db)
):
    """
    Public contact form for non-registered users.
    Stores message in DB and emails support team.
    """
    contact = ContactMessage(
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        subject=payload.subject,
        message=payload.message,
    )
    db.add(contact)
    db.commit()

    # Notify support team
    send_email(
        to="support@aptraveltemple.com",
        subject=f"[Contact Form] {payload.subject} — {payload.name}",
        body=f"From: {payload.name} <{payload.email}>\nPhone: {payload.phone}\n\n{payload.message}"
    )

    return {
        "success": True,
        "data": {},
        "message": "Thank you! Our team will get back to you within 24 hours."
    }
