"""
main.py
FastAPI application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from contextlib import asynccontextmanager
import logging

from src.core.config import settings
from src.core.redis import init_redis, close_redis
from src.core.logging import setup_logging
from src.api.v1.router import router as v1_router
from src.core.exceptions import register_exception_handlers

setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting services...")
    try:
        await init_redis()
        logger.info("Redis initialized")
    except Exception as e:
        logger.warning(f"Redis unavailable: {e}")

    yield

    try:
        await close_redis()
    except Exception as e:
        logger.warning(f"Error closing Redis: {e}")
# ─────────────────────────────────────────────
# FastAPI App
# ─────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    swagger_ui_parameters={"persistAuthorization": True},
)


# ─────────────────────────────────────────────
# CORS Middleware
# ─────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# Register Global Exception Handlers
# ─────────────────────────────────────────────
register_exception_handlers(app)


# ─────────────────────────────────────────────
# API Routes
# ─────────────────────────────────────────────
app.include_router(v1_router, prefix="/api/v1")


# ─────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────
@app.get("/api/v1/health", tags=["Health"])
async def health():
    return {
        "status": "ok",
        "version": settings.APP_VERSION
    }


# ─────────────────────────────────────────────
# Public routes — no token needed
# Everything else gets the 🔒 lock icon
# ─────────────────────────────────────────────
PUBLIC_ROUTES = {
    # Auth — no login required
    "/api/v1/auth/register",
    "/api/v1/auth/send-otp",
    "/api/v1/auth/verify-otp",
    "/api/v1/auth/resend-otp",
    "/api/v1/auth/login",
    "/api/v1/auth/login/otp",
    "/api/v1/auth/refresh-token",
    "/api/v1/auth/logout",
    "/api/v1/auth/logout-all",
    "/api/v1/auth/forgot-password",
    "/api/v1/auth/reset-password",

    # Health
    "/api/v1/health",

    # Public misc — no login needed
    "/api/v1/version",
    "/api/v1/config",
    "/api/v1/banners",
    "/api/v1/home",
    "/api/v1/districts",
    "/api/v1/cities",
    "/api/v1/languages",
    "/api/v1/currencies",
    "/api/v1/contact-us",
     # Payments — no token needed
    "/api/v1/payments/methods",
    "/api/v1/payments/webhook/razorpay",
}


# ─────────────────────────────────────────────
# Custom OpenAPI (JWT Bearer Auth)
# ─────────────────────────────────────────────
def custom_openapi():

    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        routes=app.routes,
    )

    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Paste your access_token here (without 'Bearer' prefix)",
        }
    }

    for path, path_item in openapi_schema["paths"].items():
        for method in path_item.values():
            if isinstance(method, dict):
                if path in PUBLIC_ROUTES:\
                
                    method["security"] = []                    # no lock icon
                else:
                    method["security"] = [{"BearerAuth": []}] # 🔒 lock icon

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi