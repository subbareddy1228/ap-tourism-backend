
# src/core/redis.py
import redis.asyncio as redis

redis_client = None

async def init_redis():
    global redis_client
    redis_client = await redis.from_url(
        "redis://localhost:6379", 
        decode_responses=True
    )

async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.close()

def get_redis():
    return redis_client