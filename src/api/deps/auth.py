"""
api/deps/auth.py
JWT authentication dependency
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.security import decode_token
from src.core.redis import is_jti_blacklisted
from src.core.database import get_db
from src.models.user import User

# IMPORTANT: auto_error=False prevents FastAPI from rejecting request automatically
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:

    # 1️⃣ Check Authorization header
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing"
        )

    token = credentials.credentials

    # 2️⃣ Decode JWT
    payload = decode_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    # 3️⃣ Ensure it's access token
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )

    user_id = payload.get("sub")
    jti = payload.get("jti")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token"
        )

    # 4️⃣ Check blacklist safely
    if jti:
        try:
            if await is_jti_blacklisted(jti):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token revoked"
                )
        except Exception:
            # Redis down → skip blacklist check
            pass

    # 5️⃣ Fetch user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    # 6️⃣ Check account status
    if user.status.name != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account suspended"
        )

    return user


# ───────── ROLE BASED ACCESS ─────────

def require_role(*roles: str):

    async def role_checker(current_user: User = Depends(get_current_user)):

        allowed_roles = [r.lower() for r in roles]

        if current_user.role.lower() not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        return current_user

    return role_checker


async def get_admin_user(current_user: User = Depends(require_role("admin"))):
    return current_user


async def get_partner_user(current_user: User = Depends(require_role("partner", "admin"))):
    return current_user


async def get_guide_user(current_user: User = Depends(require_role("guide", "admin"))):
    return current_user


async def get_verified_user(current_user: User = Depends(get_current_user)):

    if not current_user.is_phone_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Phone verification required"
        )

    return current_user