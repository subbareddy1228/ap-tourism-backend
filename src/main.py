"""
AP Travel & Temple — FastAPI Application
Module 6: Vehicle APIs
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1.endpoints.vehicles import router as vehicles_router

app = FastAPI(
    title="AP Travel & Temple — Vehicle APIs",
    description="Module 6: Vehicle management, fare calculation, and driver management",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(vehicles_router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "ok", "module": "M6 — Vehicle APIs"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": str(exc), "code": 500},
    )
