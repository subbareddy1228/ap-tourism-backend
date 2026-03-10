try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:swetha@localhost:5432/ap_tourism_db"
    SECRET_KEY: str = "change-this-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    RAZORPAY_KEY_ID: str = "rzp_test_xxxxxxxxxxxx"
    RAZORPAY_KEY_SECRET: str = "your_razorpay_secret"
    RAZORPAY_WEBHOOK_SECRET: str = "your_webhook_secret"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
