import logging

import redis.asyncio as aioredis

from src.core.config import settings

logger = logging.getLogger(__name__)

_redis_client: aioredis.Redis | None = None


def get_redis_client() -> aioredis.Redis | None:
    return _redis_client


async def init_redis() -> None:
    global _redis_client
    try:
        client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await client.ping()
        _redis_client = client
        logger.info("Connected to Redis")
    except Exception as exc:
        logger.warning("Redis unavailable (%s). Search history and caching disabled.", exc)
        _redis_client = None


async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
        logger.info("Redis connection closed")
