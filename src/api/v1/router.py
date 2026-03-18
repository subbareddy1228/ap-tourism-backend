from fastapi import APIRouter
from src.api.v1.endpoints.temple import router as temple_router
from src.api.v1.endpoints.darshan import router as darshan_router

router = APIRouter()

router.include_router(
    temple_router,
    prefix="/temples",
    tags=["Temples"]
)

router.include_router(
    darshan_router,
    prefix="/darshan",
    tags=["Darshan, Pooja & Prasadam"]   # keep ONLY here
)