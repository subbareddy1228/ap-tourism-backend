from fastapi import APIRouter
 
from src.api.v1.endpoints import auth, users, temple, wallet, partners
 
router = APIRouter()
 
router.include_router(auth.router, prefix="/auth", tags=["Auth"])

router.include_router(users.router, prefix="/users", tags=["Users"])

router.include_router(temple.router, prefix="/temples", tags=["Temples"])

router.include_router(wallet.router, prefix="/wallet", tags=["Wallet"])

router.include_router(partners.router, prefix="/partners", tags=["Partners"])
 