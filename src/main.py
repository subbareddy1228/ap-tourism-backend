
"""
src/main.py
FastAPI Application Entry Point — AP Tourism Backend
"""

import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.api.v1.endpoints.users import router as users_router
from src.api.v1.endpoints.wallet import router as wallet_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc} on {request.url}")
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "Internal server error", "code": 500}
    )

# ── Routers ───────────────────────────────────────────────────
app.include_router(users_router,  prefix="/api/v1")
app.include_router(wallet_router, prefix="/api/v1")

@app.get("/api/v1/health", tags=["Health"])
def health_check():
    return {"status": "ok", "version": settings.APP_VERSION}
