"""
core/security.py
JWT token creation, verification, and password hashing.

Spec compliance:
- JTI (JWT ID) added to every token — blacklist uses JTI not full token
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
import bcrypt
from src.core.config import settings

# ── Password Hashing ──────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)



# ── JWT Tokens ────────────────────────────────────────────────
def create_access_token(subject: Union[str, int], role: str, expires_delta=None) -> str:
    """Access token with JTI. Expiry: 15 min. JTI blacklisted on logout."""
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {
        "sub":  str(subject),
        "role": role,
        "type": "access",
        "jti":  str(uuid.uuid4()),   # ← blacklist key on logout
        "exp":  expire,
        "iat":  datetime.utcnow(),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: Union[str, int], role: str, expires_delta=None) -> str:
    """Refresh token with JTI. Expiry: 7 days. JTI stored in Redis, invalidated on rotation."""
    expire = datetime.utcnow() + (expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))
    payload = {
        "sub":  str(subject),
        "role": role,
        "type": "refresh",
        "jti":  str(uuid.uuid4()),   # ← stored in Redis, deleted on rotation
        "exp":  expire,
        "iat":  datetime.utcnow(),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Decode JWT. Returns payload or None if invalid/expired."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None
