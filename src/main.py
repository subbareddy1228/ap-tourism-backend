from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from src.api.v1.endpoints import partner
app = FastAPI(title="AP Tourism Backend",version="1.0.0")

# @app.get("/")
# def home():
#     return {"message": "AP Tourism API running"}

# include routers
app.include_router(partner.router)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="AP Tourism Backend",
        version="1.0.0",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi