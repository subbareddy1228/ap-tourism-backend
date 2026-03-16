from fastapi import APIRouter
from src.api.v1.endpoints import temples, darshan

router = APIRouter(prefix="/v1")
router.include_router(temples.router)
router.include_router(darshan.router)