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
from src.core.elasticsearch import init_elasticsearch, close_elasticsearch

from src.api.v1.router import router as v1_router


# ── Logging Setup ─────────────────────────────────────────────
setup_logging()

# Hide Elasticsearch INFO logs
logging.getLogger("elastic_transport").setLevel(logging.ERROR)
logging.getLogger("elasticsearch").setLevel(logging.ERROR)
logging.getLogger("src.core.elasticsearch").setLevel(logging.ERROR)


# ── Lifespan Events ───────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):

    print("Starting services...")

    await init_redis()

    try:
        await init_elasticsearch()
    except Exception as e:
        print(f"Elasticsearch unavailable: {e}. Search endpoints disabled.")

    yield

    print("Shutting down services...")

    await close_redis()
    await close_elasticsearch()


# ── FastAPI App ───────────────────────────────────────────────
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


# ── API Routes ────────────────────────────────────────────────
app.include_router(v1_router, prefix="/api/v1")


# ── Health Check ──────────────────────────────────────────────
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

                if any(tag in method.get("tags", []) for tag in ["Authentication", "Health"]):
                    method["security"] = []
                else:
                    method["security"] = [{"BearerAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi