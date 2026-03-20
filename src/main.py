import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.core.elasticsearch import init_elasticsearch, close_elasticsearch
from src.core.redis import init_redis, close_redis
from src.api.v1.endpoints.search import router as search_router

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("Starting Module 15 — Search APIs")
    await init_redis()
    await init_elasticsearch()
    yield
    logger.info("Shutting down Module 15 — Search APIs")
    await close_elasticsearch()
    await close_redis()


app = FastAPI(
    title=settings.APP_TITLE,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search_router)

    
@app.get("/health", tags=["Health"])
async def health() -> dict:
    return {"status": "ok", "module": 15, "service": "Search APIs"}
