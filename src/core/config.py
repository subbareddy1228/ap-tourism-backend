from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ap_tourism"
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = "ap-tourism-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    APP_NAME: str = "AP Tourism Backend"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    RAZORPAY_KEY_ID: str = "rzp_test_stub"
    RAZORPAY_KEY_SECRET: str = "stub_secret"

    class Config:
        env_file = ".env"

settings = Settings()
