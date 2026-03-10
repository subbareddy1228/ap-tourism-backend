from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.database import create_tables
from src.api.v1.endpoints.payments import router as payment_router
from src.api.v1.endpoints.coupons import router as coupon_router
app = FastAPI(title="AP Travel & Temple Tourism API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
#Creates all tables automatically when server starts
create_tables()
app.include_router(payment_router, prefix="/api/v1")
app.include_router(coupon_router,  prefix="/api/v1")
@app.get("/health", tags=["Health"])
def health_check():
    return {
        "success": True,
        "data": {"status": "ok", "M12": "active", "M16": "active"},
        "message": "Server is running."
    }