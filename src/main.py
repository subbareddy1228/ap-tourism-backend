from fastapi import FastAPI

from src.api.v1.endpoints import partner
from src.api.v1.endpoints import guide

app = FastAPI(title="AP Tourism Backend",version="1.0.0")

# @app.get("/")
# def home():
#     return {"message": "AP Tourism API running"}

# include routers
app.include_router(partner.router)
app.include_router(guide.router)