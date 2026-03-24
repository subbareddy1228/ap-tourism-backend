from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import admin

app = FastAPI(
    title="AP Travel & Temple — Module 19: Admin APIs",
    version="1.0.0",
    description="Admin management endpoints for the AP Tourism platform"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin.router)

@app.get("/health")
def health():
    return {"status": "ok", "module": "19 - Admin APIs"}
