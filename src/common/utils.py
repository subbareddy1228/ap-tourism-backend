"""
common/utils.py
Redis Cache Helper — shared utility used across all modules.
 
NOTE: Reuses the Redis client initialized in core/redis.py
      via init_redis() at app startup. No separate connection pool.
"""
 
import json
import logging
import random
from src.core.redis import redis_client
 
logger = logging.getLogger(__name__)
 
 
async def get_redis():
    """Return the shared Redis client from core/redis.py."""
    return redis_client

def generate_otp() -> str:
    """
    Generate a 6 digit OTP.
    """
    return str(random.randint(100000, 999999))
 
async def set_cache(key: str, value, ttl: int = 3600):
    """Store a value in Redis. value is auto-serialized to JSON."""
    r = await get_redis()
    await r.set(key, json.dumps(value), ex=ttl)
 
 
async def get_cache(key: str):
    """Retrieve value from Redis. Returns None if not found or expired."""
    r = await get_redis()
    raw = await r.get(key)
    if raw is None:
        return None
    return json.loads(raw)
 
 
async def delete_cache(key: str):
    """Delete a key from Redis."""
    r = await get_redis()
    await r.delete(key)
 
 
async def blacklist_token(jti: str, ttl_seconds: int):
    """Blacklist a JWT token by JTI."""
    await set_cache(f"blacklist:{jti}", "1", ttl=ttl_seconds)
 
 
async def is_token_blacklisted(jti: str) -> bool:
    """Returns True if this JWT has been blacklisted."""
    return await get_cache(f"blacklist:{jti}") is not None
 
 
# ── Session Helpers ───────────────────────────────────────────
 
async def save_session(user_id: str, session_id: str, session_data: dict, ttl: int = 86400 * 30):
    """Store a user session. TTL default: 30 days."""
    key = f"session:{user_id}:{session_id}"
    await set_cache(key, session_data, ttl)
 
 
async def get_all_sessions(user_id: str) -> list:
    """Return all active sessions for a user."""
    r = await get_redis()
    pattern = f"session:{user_id}:*"
 
    sessions = []
    async for key in r.scan_iter(pattern):
        data = await get_cache(key)
        if data:
            session_id = key.split(":")[-1]
            data["session_id"] = session_id
            sessions.append(data)
 
    return sessions
 
 
async def delete_session(user_id: str, session_id: str):
    """Delete a specific session."""
    await delete_cache(f"session:{user_id}:{session_id}")
 
 
async def delete_all_sessions(user_id: str):
    """Delete ALL sessions for a user."""
    r = await get_redis()
    async for key in r.scan_iter(f"session:{user_id}:*"):
        await r.delete(key)