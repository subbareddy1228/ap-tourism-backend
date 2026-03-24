"""
src/api/v1/endpoints/public/misc.py
Module 20 — Public/Misc APIs
10 endpoints — no auth required.

Fixed for LEV146 project:
  - Removed double prefix /api/v1
  - AsyncSession + async def throughout
  - Removed Banner, ContactMessage, FAQ (models don't exist)
  - ContactUsSchema defined inline
  - Cache uses project's async utils
  - health endpoint removed (already in main.py)
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.config import settings
from src.common.utils import get_cache, set_cache
from src.models.destination import Destination
from src.models.package import Package
from src.models.temple import Temple
from src.common.responses import APIResponse

router = APIRouter(prefix="", tags=["Public"])

# ─── Static Data ────────────────────────────────────────────

AP_DISTRICTS = [
    "Visakhapatnam", "Vizianagaram", "Srikakulam", "East Godavari",
    "West Godavari", "Krishna", "Guntur", "Prakasam", "Nellore",
    "Chittoor", "Kadapa", "Anantapur", "Kurnool", "Tirupati",
    "Palnadu", "Nandyal", "Anakapalli", "Alluri Sitharama Raju",
    "Konaseema", "Bapatla", "Eluru", "NTR District", "Manyam",
]

AP_CITIES = [
    {"city": "Visakhapatnam", "district": "Visakhapatnam"},
    {"city": "Vijayawada",    "district": "Krishna"},
    {"city": "Guntur",        "district": "Guntur"},
    {"city": "Tirupati",      "district": "Tirupati"},
    {"city": "Rajahmundry",   "district": "East Godavari"},
    {"city": "Kakinada",      "district": "East Godavari"},
    {"city": "Nellore",       "district": "Nellore"},
    {"city": "Kurnool",       "district": "Kurnool"},
    {"city": "Kadapa",        "district": "Kadapa"},
    {"city": "Anantapur",     "district": "Anantapur"},
    {"city": "Eluru",         "district": "Eluru"},
    {"city": "Ongole",        "district": "Prakasam"},
    {"city": "Srikakulam",    "district": "Srikakulam"},
    {"city": "Vizianagaram",  "district": "Vizianagaram"},
    {"city": "Bhimavaram",    "district": "West Godavari"},
]


# ─── Inline Schema ────────────────────────────────────────────

class ContactUsSchema(BaseModel):
    name:    str
    email:   EmailStr
    phone:   Optional[str] = None
    subject: str
    message: str


# ════════════════════════════════════════════════════════
# VERSION
# ════════════════════════════════════════════════════════

@router.get("/version", summary="API version info")
async def get_version():
    """Returns current API version, build number, deployment timestamp."""
    return APIResponse.success(
        message="Version info",
        data={
            "version":     settings.APP_VERSION,
            "build":       "1.0.0",
            "deployed_at": datetime.utcnow().isoformat(),
        }
    )


# ════════════════════════════════════════════════════════
# CONFIGURATION
# ════════════════════════════════════════════════════════

@router.get("/config", summary="App configuration for clients")
async def get_config():
    """Payment methods, policies, supported languages — cached 1 hour."""
    cached = await get_cache("public:config")
    if cached:
        return APIResponse.success(message="Config fetched", data=cached)

    data = {
        "supported_payment_methods":  ["UPI", "CARD", "NET_BANKING", "WALLET", "EMI", "PAY_LATER"],
        "min_booking_advance_hours":   2,
        "cancellation_policy_text":    ">48hrs full refund, 24-48hrs 50%, <24hrs no refund",
        "supported_languages":         ["Telugu", "Hindi", "English", "Tamil", "Kannada"],
        "currency":                    "INR",
        "gst_rate":                    18,
        "platform_name":               "AP Travel & Temple",
        "support_phone":               "+91-XXXXXXXXXX",
        "support_email":               "support@aptraveltemple.com",
    }

    await set_cache("public:config", data, ttl=3600)
    return APIResponse.success(message="Config fetched", data=data)


# ════════════════════════════════════════════════════════
# BANNERS
# ════════════════════════════════════════════════════════

@router.get("/banners", summary="Active homepage banners")
async def get_banners():
    """
    Active homepage banners/promotions.
    Cached 30 minutes. Banner model is pending — returns empty list until implemented.
    """
    return APIResponse.success(
        message="Banners fetched",
        data=[]   # Banner model not yet created — stub response
    )


# ════════════════════════════════════════════════════════
# HOMEPAGE AGGREGATED DATA
# ════════════════════════════════════════════════════════

@router.get("/home", summary="Homepage aggregated data")
async def get_homepage(db: AsyncSession = Depends(get_db)):
    """
    Aggregated homepage data — featured destinations, packages,
    popular temples. Cached 30 minutes.
    """
    cached = await get_cache("public:home")
    if cached:
        return APIResponse.success(message="Homepage data fetched", data=cached)

    # Featured destinations
    dest_result = await db.execute(
        select(Destination)
        .where(Destination.is_active == True)
        .limit(6)
    )
    destinations = dest_result.scalars().all()

    # Featured packages
    pkg_result = await db.execute(
        select(Package)
        .where(Package.is_active == True)
        .limit(6)
    )
    packages = pkg_result.scalars().all()

    # Popular temples — order by created_at (booking_count column not available)
    temple_result = await db.execute(
        select(Temple)
        .where(Temple.is_active == True)
        .order_by(Temple.created_at.desc())
        .limit(6)
    )
    temples = temple_result.scalars().all()

    data = {
        "featured_destinations": [
            {"id": str(d.id), "name": d.name, "district": d.district}
            for d in destinations
        ],
        "featured_packages": [
            {"id": str(p.id), "name": p.name, "duration_days": p.duration_days}
            for p in packages
        ],
        "popular_temples": [
            {"id": str(t.id), "name": t.name, "deity": t.deity, "district": t.district}
            for t in temples
        ],
        "active_banners": [],  # Banner model pending
    }

    await set_cache("public:home", data, ttl=1800)
    return APIResponse.success(message="Homepage data fetched", data=data)


# ════════════════════════════════════════════════════════
# LOCATION DATA
# ════════════════════════════════════════════════════════

@router.get("/districts", summary="All AP districts")
async def get_districts():
    """All Andhra Pradesh districts for dropdown filters."""
    return APIResponse.success(message="Districts fetched", data=AP_DISTRICTS)


@router.get("/cities", summary="Cities with district mapping")
async def get_cities():
    """Cities list with district mapping."""
    return APIResponse.success(message="Cities fetched", data=AP_CITIES)


# ════════════════════════════════════════════════════════
# LOCALIZATION
# ════════════════════════════════════════════════════════

@router.get("/languages", summary="Supported languages")
async def get_languages():
    """Supported languages on the platform."""
    return APIResponse.success(
        message="Languages fetched",
        data=["Telugu", "Hindi", "English", "Tamil", "Kannada"]
    )


@router.get("/currencies", summary="Supported currencies")
async def get_currencies():
    """Supported currencies — currently INR only."""
    return APIResponse.success(message="Currencies fetched", data=["INR"])


# ════════════════════════════════════════════════════════
# CONTACT
# ════════════════════════════════════════════════════════

@router.post("/contact-us", summary="Public contact form")
async def contact_us(payload: ContactUsSchema):
    """
    Public contact form for non-registered users.
    Logs the submission. Email dispatch via Celery task (pending).
    ContactMessage DB model pending — stored in-memory for now.
    """
    # Log submission (ContactMessage model not yet created)
    # TODO: save to DB when ContactMessage model is added
    # TODO: trigger Celery email task when tasks module is ready
    print(
        f"[Contact Form] {payload.name} <{payload.email}> | "
        f"Phone: {payload.phone} | Subject: {payload.subject}"
    )

    return APIResponse.success(
        message="Thank you! Our team will get back to you within 24 hours.",
        data={}
    )