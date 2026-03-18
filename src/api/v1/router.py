from fastapi import APIRouter
from src.api.v1.endpoints import auth, users, temples, wallet, partner, darshan

router = APIRouter()

router.include_router(auth.router)
router.include_router(users.router)
router.include_router(temples.router)
router.include_router(darshan.router)
router.include_router(wallet.router)
router.include_router(partner.router)