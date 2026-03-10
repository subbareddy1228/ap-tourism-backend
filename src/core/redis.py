from typing import Optional
import redis as redis_lib
from src.core.config import settings

_redis_client: Optional[redis_lib.Redis] = None


def get_redis_client() -> Optional[redis_lib.Redis]:
    global _redis_client
    if _redis_client is None and settings.REDIS_URL:
        _redis_client = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


def get_redis():
    """FastAPI dependency — yields Redis client (or None if not configured)."""
    yield get_redis_client()