from fastapi import APIRouter
from src.api.v1.endpoints import hotels

api_router = APIRouter()

api_router.include_router(
    hotels.router,
    prefix="/hotels",
    tags=["Hotel Partner APIs"]
)
