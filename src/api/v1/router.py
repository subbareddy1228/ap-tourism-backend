from fastapi import APIRouter
from src.api.v1.endpoints import temple, darshan

router = APIRouter()


router.include_router(temple.router)
router.include_router(darshan.router)
