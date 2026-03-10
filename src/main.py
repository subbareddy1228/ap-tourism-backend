"""
main.py
FastAPI application entry point.
 
CHANGED in M2:
  - Imported users router
  - Registered users router at /api/v1
"""
 
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
 
from src.core.config import settings
from src.core.redis import init_redis, close_redis
from src.core.logging import setup_logging
 
from src.api.v1.endpoints.auth import router as auth_router
from src.api.v1.endpoints.users import router as users_router  # ← M2
 
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
 