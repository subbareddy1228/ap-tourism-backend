import redis
import json
import os

_redis = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))


def get_cache(key: str):
    try:
        value = _redis.get(key)
        return json.loads(value) if value else None
    except Exception:
        return None


def set_cache(key: str, value, ttl: int = 300):
    try:
        _redis.setex(key, ttl, json.dumps(value, default=str))
    except Exception:
        pass


def delete_cache(key: str):
    try:
        _redis.delete(key)
    except Exception:
        pass