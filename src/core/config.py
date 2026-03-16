from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:sonu12@localhost/ap_tourism"
    REDIS_URL: str = "redis://localhost:6379"
    DEBUG: bool = True

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()