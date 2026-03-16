from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # type: ignore

from src.api.v1.router import router as v1_router
from src.core.middleware import RequestLoggingMiddleware
from src.core.logging import setup_logging

setup_logging()

app = FastAPI(
    title="AP Tourism Backend",
    description="Andhra Pradesh Tourism Portal — Temple, Darshan & Pilgrimage APIs",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.add_middleware(RequestLoggingMiddleware)

app.include_router(v1_router, prefix="/api")


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "version": "1.0.0"}