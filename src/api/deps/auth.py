"""
api/deps/auth.py
JWT auth dependency — checks JTI blacklist (not full token).
Role-based access control helpers.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.security import decode_token
from src.core.redis import is_jti_blacklisted
from src.core.database import get_db
from src.models.user import User

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Validates JWT and returns current user.
    Checks JTI blacklist — catches logged-out tokens instantly.
    """
    token = credentials.credentials

    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise invalid

    # Check JTI blacklist (set on logout)
    jti = payload.get("jti")
    if not jti or await is_jti_blacklisted(jti):
        raise invalid

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise invalid

    if user.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account suspended.")

    return user


def require_role(*roles: str):
    """Role-based access dependency factory."""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required: {', '.join(roles)}"
            )
        return current_user
    return role_checker


async def get_admin_user(current_user: User = Depends(require_role("admin"))) -> User:
    return current_user

async def get_partner_user(current_user: User = Depends(require_role("partner", "admin"))) -> User:
    return current_user

async def get_guide_user(current_user: User = Depends(require_role("guide", "admin"))) -> User:
    return current_user

async def get_verified_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_phone_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Phone verification required.")
    return current_user
