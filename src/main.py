from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.core.config import settings
from src.core.database import Base, engine
from src.api.v1.router import api_router
import src.models


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)  # ✅ async-safe table creation
    yield


app = FastAPI(
    title       = "Hotel Partner APIs",
    description = "AP Travel & Temple Tourism — Hotel Partner Management (Auth disabled for testing)",
    version     = settings.APP_VERSION,
    docs_url    = "/docs",
    redoc_url   = "/redoc",
    lifespan    = lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["Health"])
def root():
    return {
        "success": True,
        "message": "Hotel Partner APIs — Running! Auth disabled for testing.",
        "version": settings.APP_VERSION,
        "total_endpoints": 14,
        "docs": "/docs"
    }


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}