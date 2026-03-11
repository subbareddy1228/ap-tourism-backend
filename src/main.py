"""
main.py
FastAPI application entry point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fastapi.openapi.utils import get_openapi

from src.core.config import settings
from src.core.redis import init_redis, close_redis
from src.core.logging import setup_logging

from src.api.v1.endpoints.auth import router as auth_router
from src.api.v1.endpoints.users import router as users_router


setup_logging()


# ───────────────────────── Redis Lifecycle ─────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_redis()
    yield
    await close_redis()


# ───────────────────────── FastAPI App ─────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    swagger_ui_parameters={"persistAuthorization": True},
)


# ───────────────────────── CORS ─────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ───────────────────────── Routers ─────────────────────────

app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")


# ───────────────────────── Health Check ─────────────────────────

@app.get("/api/v1/health", tags=["Health"])
async def health():
    return {"status": "ok", "version": settings.APP_VERSION}


# ───────────────────────── Swagger Bearer Fix ─────────────────────────

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="AP Tourism Backend API",
        routes=app.routes,
    )

    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }

    # Remove locks from all endpoints
    for path in openapi_schema["paths"].values():
        for method in path.values():
            method["security"] = []

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi