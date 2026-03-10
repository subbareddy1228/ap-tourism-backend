"""
core/redis.py
Redis client — OTP storage, JTI blacklist, resend rate limit, session management.

Spec compliance:
- Blacklist uses JTI (not full token) as Redis key
- Resend rate limit: max 3 resends per 10 min per phone
- Refresh token stored by JTI (rotated on use)
"""

import redis.asyncio as aioredis
from src.core.config import settings

redis_client: aioredis.Redis = None


async def get_redis() -> aioredis.Redis:
    return redis_client


async def init_redis():
    global redis_client
    redis_client = await aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True
    )


async def close_redis():
    if redis_client:
        await redis_client.close()


# ── OTP Storage ───────────────────────────────────────────────
# Key: otp:{purpose}:{phone}  TTL: 5 min

async def store_otp(phone: str, otp: str, purpose: str = "register") -> None:
    """Store OTP with 5 min TTL. Key = otp:{purpose}:{phone}"""
    key = f"otp:{purpose}:{phone}"
    await redis_client.setex(key, settings.OTP_EXPIRE_SECONDS, otp)


async def get_otp(phone: str, purpose: str = "register") -> str | None:
    key = f"otp:{purpose}:{phone}"
    return await redis_client.get(key)


async def delete_otp(phone: str, purpose: str = "register") -> None:
    key = f"otp:{purpose}:{phone}"
    await redis_client.delete(key)


# ── OTP Resend Rate Limit ─────────────────────────────────────
# Spec: max 3 resends per 10 minutes per phone

async def increment_resend_count(phone: str) -> int:
    """
    Increment resend counter for a phone number.
    Counter expires after 10 minutes.
    Returns current count.
    """
    key = f"otp_resend_count:{phone}"
    count = await redis_client.incr(key)
    if count == 1:
        # Set 10 min window on first resend
        await redis_client.expire(key, settings.OTP_RESEND_WINDOW_SECONDS)
    return count


async def get_resend_count(phone: str) -> int:
    """Get how many times OTP was resent in current window."""
    key = f"otp_resend_count:{phone}"
    val = await redis_client.get(key)
    return int(val) if val else 0


async def get_resend_ttl(phone: str) -> int:
    """Get remaining seconds in the resend window."""
    key = f"otp_resend_count:{phone}"
    return await redis_client.ttl(key)


# ── OTP Attempt Tracking ──────────────────────────────────────

async def increment_otp_attempts(phone: str) -> int:
    key = f"otp_attempts:{phone}"
    count = await redis_client.incr(key)
    await redis_client.expire(key, settings.OTP_EXPIRE_SECONDS)
    return count


async def clear_otp_attempts(phone: str) -> None:
    key = f"otp_attempts:{phone}"
    await redis_client.delete(key)


# ── JTI Blacklist (Logout) ────────────────────────────────────
# Spec: blacklist JTI (not full token) with TTL = token remaining expiry

async def blacklist_jti(jti: str, expire_seconds: int) -> None:
    """
    Blacklist a token by its JTI on logout.
    TTL = remaining expiry time of the token.
    Key: blacklist:jti:{jti}
    """
    key = f"blacklist:jti:{jti}"
    await redis_client.setex(key, expire_seconds, "1")


async def is_jti_blacklisted(jti: str) -> bool:
    """Check if a JTI has been blacklisted (token was logged out)."""
    key = f"blacklist:jti:{jti}"
    return await redis_client.exists(key) == 1


# ── Refresh Token Storage (by JTI) ───────────────────────────
# Spec: validate refresh token in Redis, invalidate old on rotation

async def store_refresh_jti(user_id: str, device_id: str, jti: str) -> None:
    """
    Store refresh token JTI per device.
    Key: refresh:{user_id}:{device_id} → jti value
    TTL: 7 days
    """
    key = f"refresh:{user_id}:{device_id}"
    expire = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
    await redis_client.setex(key, expire, jti)


async def get_refresh_jti(user_id: str, device_id: str) -> str | None:
    """Get stored JTI for a device."""
    key = f"refresh:{user_id}:{device_id}"
    return await redis_client.get(key)


async def delete_refresh_jti(user_id: str, device_id: str) -> None:
    """Remove refresh token for a device (single device logout)."""
    key = f"refresh:{user_id}:{device_id}"
    await redis_client.delete(key)


async def delete_all_refresh_jtis(user_id: str) -> None:
    """Remove all refresh tokens for a user (logout all devices)."""
    pattern = f"refresh:{user_id}:*"
    keys = await redis_client.keys(pattern)
    if keys:
        await redis_client.delete(*keys)


# ── Store refresh token (backward compat alias) ───────────────
async def store_refresh_token(user_id: str, device_id: str, token: str) -> None:
    """Alias kept for compatibility — stores full token string."""
    key = f"refresh:{user_id}:{device_id}"
    expire = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
    await redis_client.setex(key, expire, token)


async def delete_refresh_token(user_id: str, device_id: str) -> None:
    await delete_refresh_jti(user_id, device_id)


async def delete_all_refresh_tokens(user_id: str) -> None:
    await delete_all_refresh_jtis(user_id)
