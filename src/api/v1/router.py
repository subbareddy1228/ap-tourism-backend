from fastapi import APIRouter
from src.api.v1.endpoints import auth, users, wallet, partner

router = APIRouter()

router.include_router(auth.router)
router.include_router(users.router)
router.include_router(wallet.router)
router.include_router(partner.router)