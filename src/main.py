from contextlib import asynccontextmanager
from fastapi import FastAPI

from src.core.database import Base, engine
from src.models.package import Package
from src.api.v1.endpoints.packages import router as package_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup — create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # shutdown
    await engine.dispose()


app = FastAPI(title="AP Tourism Backend", lifespan=lifespan)

app.include_router(package_router, prefix="/api/v1")