from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "AP Travel & Temple Tourism"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379"

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    UPLOAD_DIR: str = "uploads/hotels"

    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "ap-south-1"
    AWS_S3_BUCKET_NAME: str = "ap-tourism-assets"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
