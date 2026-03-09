# ============================================================
# app/utils/cache.py
# Redis Cache Helper — shared utility
# Used by: sessions (LEV146), OTP (LEV148), etc.
# ============================================================

import os
import json
import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

_redis_client = None


def get_redis() -> redis.Redis:
    """Return singleton Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client


def set_cache(key: str, value, ttl: int = 3600):
    """
    Store a value in Redis.
    - value: can be dict, list, str, int — auto-serialized to JSON
    - ttl: seconds until expiry (default 1 hour)
    """
    r = get_redis()
    r.set(key, json.dumps(value), ex=ttl)


def get_cache(key: str):
    """
    Retrieve a value from Redis.
    Returns None if key doesn't exist or is expired.
    """
    r = get_redis()
    raw = r.get(key)
    if raw is None:
        return None
    return json.loads(raw)


def delete_cache(key: str):
    """Delete a key from Redis."""
    get_redis().delete(key)


def blacklist_token(jti: str, ttl_seconds: int):
    """
    Blacklist a JWT token by its JTI (JWT ID).
    Used by logout and session revoke.
    Key: blacklist:{jti}
    """
    set_cache(f"blacklist:{jti}", "1", ttl=ttl_seconds)


def is_token_blacklisted(jti: str) -> bool:
    """Returns True if this JWT has been blacklisted (logged out)."""
    return get_cache(f"blacklist:{jti}") is not None


# ---- Session helpers (used by /me/sessions endpoints) ----

def save_session(user_id: str, session_id: str, session_data: dict, ttl: int = 86400 * 30):
    """
    Store a user session in Redis.
    Key pattern: session:{user_id}:{session_id}
    TTL default: 30 days
    """
    key = f"session:{user_id}:{session_id}"
    set_cache(key, session_data, ttl=ttl)


def get_all_sessions(user_id: str) -> list:
    """Return all active sessions for a user."""
    r = get_redis()
    pattern = f"session:{user_id}:*"
    keys = r.keys(pattern)
    sessions = []
    for key in keys:
        data = get_cache(key)
        if data:
            session_id = key.split(":")[-1]
            data["session_id"] = session_id
            sessions.append(data)
    return sessions


def delete_session(user_id: str, session_id: str):
    """Delete a specific session (used by DELETE /me/sessions/{id})."""
    delete_cache(f"session:{user_id}:{session_id}")


def delete_all_sessions(user_id: str):
    """Delete ALL sessions for a user (used by logout-all)."""
    r = get_redis()
    keys = r.keys(f"session:{user_id}:*")
    for key in keys:
        r.delete(key)




# ============================================================
# app/utils/s3.py
# AWS S3 Upload Helper
# Used by: PATCH /me/avatar (LEV146)
# ============================================================

import os
import uuid
import boto3
from fastapi import UploadFile, HTTPException
from botocore.exceptions import ClientError

S3_BUCKET      = os.getenv("AWS_S3_BUCKET", "ap-tourism-media")
S3_REGION      = os.getenv("AWS_REGION",    "ap-south-1")
CLOUDFRONT_URL = os.getenv("CLOUDFRONT_URL", f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com")

ALLOWED_AVATAR_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
MAX_AVATAR_SIZE_MB   = 5
MAX_AVATAR_BYTES     = MAX_AVATAR_SIZE_MB * 1024 * 1024


def get_s3_client():
    return boto3.client(
        "s3",
        region_name=S3_REGION,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )


async def upload_avatar(file: UploadFile, user_id: str) -> str:
    """
    Validates and uploads a user avatar to S3.
    Returns the CloudFront URL of the uploaded image.

    Raises HTTPException:
      - 400 if file type is not allowed
      - 400 if file size exceeds 5MB
      - 500 if S3 upload fails
    """

    # --- Validate content type ---
    if file.content_type not in ALLOWED_AVATAR_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: jpeg, jpg, png, webp"
        )

    # --- Read file content and check size ---
    content = await file.read()
    if len(content) > MAX_AVATAR_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {MAX_AVATAR_SIZE_MB}MB"
        )

    # --- Build unique S3 key ---
    extension = file.content_type.split("/")[-1].replace("jpeg", "jpg")
    s3_key    = f"avatars/{user_id}/{uuid.uuid4()}.{extension}"

    # --- Upload to S3 ---
    try:
        s3 = get_s3_client()
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=content,
            ContentType=file.content_type,
            ACL="public-read",
        )
    except ClientError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload avatar: {str(e)}"
        )

    return f"{CLOUDFRONT_URL}/{s3_key}"


async def delete_s3_file(url: str):
    """
    Deletes an S3 file given its CloudFront URL.
    Used when replacing an existing avatar.
    Silent fail — does not raise if file not found.
    """
    if not url or CLOUDFRONT_URL not in url:
        return

    try:
        s3_key = url.replace(f"{CLOUDFRONT_URL}/", "")
        s3 = get_s3_client()
        s3.delete_object(Bucket=S3_BUCKET, Key=s3_key)
    except Exception:
        pass  # Non-critical — silently ignore
