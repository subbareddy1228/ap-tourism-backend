"""
src/services/__init__.py
Re-exports all service modules so endpoints can do:
  from src.services import user_service, wallet_service, etc.
"""

from src.services import (
    admin_service,
    analytics_service,
    auth_service,
    booking_service,
    coupon_service,
    darshan_service,
    destination_service,
    guide_service,
    hotel_service,
    notification_service,
    package_service,
    partner_service,
    payment_service,
    review_service,
    search_service,
    support_service,
    temple_service,
    tracking_service,
    user_service,
    vehicle_service,
    wallet_service,
)

__all__ = [
    "admin_service", "analytics_service", "auth_service",
    "booking_service", "coupon_service", "darshan_service",
    "destination_service", "guide_service", "hotel_service",
    "notification_service", "package_service", "partner_service",
    "payment_service", "review_service", "search_service",
    "support_service", "temple_service", "tracking_service",
    "user_service", "vehicle_service", "wallet_service",
]