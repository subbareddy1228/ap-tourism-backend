from fastapi import APIRouter
from src.api.v1.endpoints import (
    admin, auth, bookings, coupons, 
    destination, guide, notifications, packages, payments, 
    reviews, users, vehicles, wallet, partner, temple, darshan, 
    hotels, search, support, tracking,
    maps,           # [MAPS] new
)
from src.api.v1.endpoints.public import misc

router = APIRouter()

router.include_router(auth.router)
router.include_router(users.router)
router.include_router(wallet.router)
router.include_router(partner.router)
router.include_router(temple.router)
router.include_router(darshan.router)
router.include_router(hotels.router)
router.include_router(vehicles.router)
router.include_router(guide.router)
router.include_router(destination.router)
router.include_router(packages.router)
router.include_router(bookings.router)
router.include_router(payments.router)
router.include_router(coupons.router)
router.include_router(reviews.router)
router.include_router(search.router)
router.include_router(notifications.router)
router.include_router(support.router)
router.include_router(tracking.router)
router.include_router(maps.router)   # [MAPS] new
router.include_router(admin.router)
router.include_router(misc.router)
