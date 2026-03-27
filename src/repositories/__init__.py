"""
repositories/__init__.py
Convenience re-exports for all repository modules.
Import: from src.repositories import booking_repo, wallet_repo, etc.
"""

from src.repositories import (
    booking_repo,
    coupon_repo,
    darshan_repo,
    destination_repo,
    guide_repo,
    hotel_repo,
    package_repo,
    partner_repo,
    review_repo,
    support_repo,
    temple_repo,
    transaction_repo,
    user_repo,
    vehicle_repo,
    wallet_repo,
)

__all__ = [
    "booking_repo",
    "coupon_repo",
    "darshan_repo",
    "destination_repo",
    "guide_repo",
    "hotel_repo",
    "package_repo",
    "partner_repo",
    "review_repo",
    "support_repo",
    "temple_repo",
    "transaction_repo",
    "user_repo",
    "vehicle_repo",
    "wallet_repo",
]