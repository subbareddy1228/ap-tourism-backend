from fastapi import APIRouter
from src.api.v1.endpoints import auth, guide, users, vehicles, wallet, partner, temple, darshan, hotels

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