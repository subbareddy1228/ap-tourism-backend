"""
api/deps/auth.py
JWT auth dependency — checks JTI blacklist.
Role-based access control helpers.
"""

import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.security import decode_token
from src.core.redis import is_jti_blacklisted
from src.core.database import get_db
from src.models.user import User
from src.common.enums import UserRole, UserStatus


logger = logging.getLogger(__name__)

# Bearer token scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Validates JWT and returns the authenticated user.
    Also checks Redis JTI blacklist.
    """

    # Check authorization header
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
        )

    token = credentials.credentials
    payload = decode_token(token)

    if not payload or payload.get("type") != "access":
        logger.warning("Invalid token used")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check JTI blacklist (logout protection)
    jti = payload.get("jti")

    if not jti or await is_jti_blacklisted(jti):
        logger.warning("Blacklisted token used")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token revoked or invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch user
    user_id = payload.get("sub")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        logger.warning("User not found for token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    # Check account status
    if user.status != UserStatus.ACTIVE:
        logger.warning("Inactive user attempted access")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account suspended",
        )

    logger.info(f"Authenticated user {user.id}")

    return user


def require_role(*roles: UserRole):
    """
    Role-based access dependency factory.
    """

    async def role_checker(current_user: User = Depends(get_current_user)) -> User:

        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join([r.value for r in roles])}",
            )

        return current_user

    return role_checker


# Role helper dependencies

async def get_admin_user(
    current_user: User = Depends(require_role(UserRole.ADMIN))
) -> User:
    return current_user


async def get_partner_user(
    current_user: User = Depends(require_role(UserRole.PARTNER, UserRole.ADMIN))
) -> User:
    return current_user


async def get_guide_user(
    current_user: User = Depends(require_role(UserRole.GUIDE, UserRole.ADMIN))
) -> User:
    return current_user


async def get_verified_user(
    current_user: User = Depends(get_current_user)
) -> User:

    if not current_user.is_phone_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Phone verification required",
        )

    return current_user