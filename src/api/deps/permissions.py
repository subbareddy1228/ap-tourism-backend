"""
api/deps/permissions.py
Role-based permission helpers for FastAPI dependency injection.
Extends auth.py with fine-grained resource-level checks.
"""

from uuid import UUID
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.database import get_db
from src.api.deps.auth import get_current_user
from src.models.user import User
from src.models.partner import Partner


# ── Resource Ownership Checks ─────────────────────────────────

async def verify_partner_ownership(
    partner_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Partner:
    """
    Verify that the current user owns the partner record.
    Admins can access any partner.
    """
    result = await db.execute(select(Partner).where(Partner.id == partner_id))
    partner = result.scalar_one_or_none()

    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partner not found"
        )

    role = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)

    if role != "admin" and str(partner.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource"
        )

    return partner


async def verify_self_or_admin(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Verify the current user is accessing their own resource or is admin.
    """
    role = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)

    if role != "admin" and str(current_user.id) != str(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own resources"
        )

    return current_user


# ── Permission Flags ──────────────────────────────────────────

def is_admin(user: User) -> bool:
    role = user.role.value if hasattr(user.role, "value") else str(user.role)
    return role == "admin"


def is_partner(user: User) -> bool:
    role = user.role.value if hasattr(user.role, "value") else str(user.role)
    return role in ("partner", "admin")


def is_guide(user: User) -> bool:
    role = user.role.value if hasattr(user.role, "value") else str(user.role)
    return role in ("guide", "admin")


def is_verified_user(user: User) -> bool:
    return user.is_phone_verified


def check_active(user: User) -> None:
    """Raise 403 if user account is not active."""
    status_val = user.status.value if hasattr(user.status, "value") else str(user.status)
    if status_val not in ("active",):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been suspended. Contact support."
        )