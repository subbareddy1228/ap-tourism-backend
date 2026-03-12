"""
core/redis.py
Redis client — OTP storage, JTI blacklist, resend rate limit, session management.

Spec compliance:
- Blacklist uses JTI (not full token) as Redis key
- Resend rate limit: max 3 resends per 10 min per phone
- Refresh token stored by JTI (rotated on use)
"""

import redis.asyncio as aioredis
from typing import Optional
from src.core.config import settings


redis_client: Optional[aioredis.Redis] = None


# ───────────────── Redis Lifecycle ─────────────────

async def init_redis() -> None:
    """Initialize Redis connection."""
    global redis_client

    redis_client = aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True
    )


async def get_redis() -> aioredis.Redis:
    """Return Redis client."""
    if redis_client is None:
        raise RuntimeError("Redis not initialized. Call init_redis() on startup.")
    return redis_client


async def close_redis() -> None:
    """Close Redis connection."""
    global redis_client

    if redis_client:
        await redis_client.close()
        redis_client = None


# ── OTP Storage ───────────────────────────────────────────────
# Key: otp:{purpose}:{phone}

async def store_otp(phone: str, otp: str, purpose: str = "register") -> None:

    r = await get_redis()

    key = f"otp:{purpose}:{phone}"

    await r.setex(
        key,
        settings.OTP_EXPIRE_SECONDS,
        otp
    )


async def get_otp(phone: str, purpose: str = "register") -> Optional[str]:

    r = await get_redis()

    key = f"otp:{purpose}:{phone}"

    return await r.get(key)


async def delete_otp(phone: str, purpose: str = "register") -> None:

    r = await get_redis()

    key = f"otp:{purpose}:{phone}"

    await r.delete(key)


# ── OTP Resend Rate Limit ─────────────────────────────────────
# Max 3 resends per window

async def increment_resend_count(phone: str) -> int:

    r = await get_redis()

    key = f"otp_resend_count:{phone}"

    count = await r.incr(key)

    if count == 1:
        await r.expire(key, settings.OTP_RESEND_WINDOW_SECONDS)

    return count


async def get_resend_count(phone: str) -> int:

    r = await get_redis()

    key = f"otp_resend_count:{phone}"

    val = await r.get(key)

    return int(val) if val else 0


async def get_resend_ttl(phone: str) -> int:

    r = await get_redis()

    key = f"otp_resend_count:{phone}"

    return await r.ttl(key)


# ── OTP Attempt Tracking ──────────────────────────────────────

async def increment_otp_attempts(phone: str) -> int:

    r = await get_redis()

    key = f"otp_attempts:{phone}"

    count = await r.incr(key)

    await r.expire(key, settings.OTP_EXPIRE_SECONDS)

    return count


async def clear_otp_attempts(phone: str) -> None:

    r = await get_redis()

    key = f"otp_attempts:{phone}"

    await r.delete(key)


# ── JTI Blacklist (Logout) ────────────────────────────────────

async def blacklist_jti(jti: str, expire_seconds: int) -> None:

    r = await get_redis()

    key = f"blacklist:jti:{jti}"

    await r.setex(key, expire_seconds, "1")


async def is_jti_blacklisted(jti: str) -> bool:

    r = await get_redis()

    key = f"blacklist:jti:{jti}"

    return await r.exists(key) == 1


# ── Refresh Token Storage ─────────────────────────────────────

async def store_refresh_jti(user_id: str, device_id: str, jti: str) -> None:

    r = await get_redis()

    key = f"refresh:{user_id}:{device_id}"

    expire = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400

    await r.setex(key, expire, jti)


async def get_refresh_jti(user_id: str, device_id: str) -> Optional[str]:

    r = await get_redis()

    key = f"refresh:{user_id}:{device_id}"

    return await r.get(key)


async def delete_refresh_jti(user_id: str, device_id: str) -> None:

    r = await get_redis()

    key = f"refresh:{user_id}:{device_id}"

    await r.delete(key)


async def delete_all_refresh_jtis(user_id: str) -> None:

    r = await get_redis()

    pattern = f"refresh:{user_id}:*"

    async for key in r.scan_iter(pattern):
        await r.delete(key)


# ── Compatibility Helpers ─────────────────────────────────────

async def store_refresh_token(user_id: str, device_id: str, token: str) -> None:

    r = await get_redis()

    key = f"refresh:{user_id}:{device_id}"

    expire = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400

    await r.setex(key, expire, token)


async def delete_refresh_token(user_id: str, device_id: str) -> None:

    await delete_refresh_jti(user_id, device_id)


async def delete_all_refresh_tokens(user_id: str) -> None:

    await delete_all_refresh_jtis(user_id)