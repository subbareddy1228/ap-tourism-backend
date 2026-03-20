from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    APP_TITLE: str = "AP Travel & Temple — Module 15: Search APIs"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = (
        "Elasticsearch-powered search across temples, hotels, packages, and destinations. "
        "Includes global search, autocomplete, suggestions, recent searches, "
        "and per-entity faceted search with aggregations."
    )
    DEBUG: bool = False

    # CORS
    ALLOWED_ORIGINS: list[str] = ["*"]

    # Elasticsearch
    ELASTICSEARCH_URL: str = "http://localhost:9200"
    ELASTICSEARCH_MAX_RETRIES: int = 5
    ELASTICSEARCH_RETRY_DELAY: int = 3

    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_SUGGESTIONS_TTL: int = 300          # 5 minutes
    REDIS_RECENT_SEARCHES_TTL: int = 604800   # 7 days
    REDIS_RECENT_SEARCHES_MAX: int = 10

    # Database (PostgreSQL — shared with other modules)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:0606@localhost:5432/ap_tourism"

    # JWT (used by deps/auth.py to decode tokens from other modules)
    SECRET_KEY: str = "change-this-secret-key-in-production"
    ALGORITHM: str = "HS256"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


settings = Settings()
