from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.v1.endpoints.coupons import router as coupon_router
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        from src.database import create_tables
        import asyncio, inspect
        if inspect.iscoroutinefunction(create_tables):
            await create_tables()
        else:
            create_tables()
        print("DB tables ready")
    except Exception as e:
        print(f"DB init skipped: {e}")
    yield


app = FastAPI(
    title="AP Travel API — Module 16 Coupon",
    description="Coupon APIs: validate, apply, remove, referral, admin CRUD",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(coupon_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "module": "coupon"}