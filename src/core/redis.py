
import redis.asyncio as aioredis
from src.core.config import settings

redis_client = None

async def init_redis():
    global redis_client
    redis_client = aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True
    )

async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.close()

def get_redis():
    return redis_client