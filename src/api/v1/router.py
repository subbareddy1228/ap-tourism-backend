# """
# api/v1/routers/temple.py  (the router file your notebook shows)
# Combines temple.py endpoints + darshan.py endpoints
# under the single prefix /temples
# """
# from fastapi import APIRouter

# from src.api.v1.endpoints.temple  import router as temple_endpoints
# from src.api.v1.endpoints.darshan import router as darshan_endpoints

# # Single router exposed to main.py
# router = APIRouter(prefix="/temples", tags=["Temples"])

# router.include_router(temple_endpoints)   # temple info + admin
# router.include_router(darshan_endpoints)  # darshan, pooja, prasadam
from fastapi import APIRouter
from src.api.v1.endpoints import temples as temple, darshan

router = APIRouter(prefix="/v1")
router.include_router(temple.router)
router.include_router(darshan.router)