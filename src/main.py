from fastapi import FastAPI

from src.core.database import Base, engine
from src.models.package import Package
from src.api.v1.endpoints.packages import router as package_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AP Tourism Backend")

app.include_router(package_router, prefix="/api/v1")