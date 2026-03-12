"""
main.py
FastAPI application entry point.

CHANGED in M2:
  - Imported users router
  - Registered users router at /api/v1

CHANGED in M3:
  - Added Swagger Bearer auth with persistAuthorization
  - Added custom OpenAPI schema with BearerAuth security scheme
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from contextlib import asynccontextmanager

from src.core.config import settings
from src.core.redis import init_redis, close_redis
from src.core.logging import setup_logging

from src.api.v1.endpoints.auth import router as auth_router
from src.api.v1.endpoints.users import router as users_router

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    await init_redis()
    yield
    await close_redis()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    swagger_ui_parameters={"persistAuthorization": True},
)

# ── CORS ──────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────
app.include_router(auth_router,  prefix="/api/v1")   # M1 — Auth
app.include_router(users_router, prefix="/api/v1")   # M2 — Users


@app.get("/api/v1/health", tags=["Health"])
async def health():
    return {"status": "ok", "version": settings.APP_VERSION}


# ── Custom OpenAPI with Bearer Auth ───────────────────────────
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        routes=app.routes,
    )

    # Add Bearer token security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Paste your access_token here (without 'Bearer' prefix)",
        }
    }

    # Apply security to all routes except auth and health
    for path, path_item in openapi_schema["paths"].items():
        for method in path_item.values():
            if isinstance(method, dict):
                # Skip public endpoints
                if any(tag in method.get("tags", []) for tag in ["Authentication", "Health"]):
                    method["security"] = []
                else:
                    method["security"] = [{"BearerAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi