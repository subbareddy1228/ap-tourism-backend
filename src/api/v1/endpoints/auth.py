
from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.get("/health")
async def auth_health():
    return {"status": "auth ok"}