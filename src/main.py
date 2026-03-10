from fastapi import FastAPI
from src.api.v1.endpoints.destination import router as destination_router

app = FastAPI()

app.include_router(destination_router, prefix="/api/v1")

