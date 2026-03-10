"""
repositories/user_repo.py
Database query helpers for Users Module.
Owner: Dev 2
"""

import logging
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from uuid import UUID

from src.models.user import User
from src.models.user_profile import UserProfile, Address, FamilyMember, UserSession

logger = logging.getLogger(__name__)


# ── User ──────────────────────────────────────────────────────

async def get_user_by_id(user_id: str, db: AsyncSession) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_phone(phone: str, db: AsyncSession) -> Optional[User]:
    result = await db.execute(select(User).where(User.phone == phone))
    return result.scalar_one_or_none()


# ── UserProfile ───────────────────────────────────────────────

async def get_profile_by_user_id(user_id: str, db: AsyncSession) -> Optional[UserProfile]:
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def create_profile(user_id: str, db: AsyncSession) -> UserProfile:
    profile = UserProfile(user_id=user_id, preferences={})
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


# ── Address ───────────────────────────────────────────────────

async def get_address_by_id(address_id: str, user_id: str, db: AsyncSession) -> Optional[Address]:
    result = await db.execute(
        select(Address).where(Address.id == address_id, Address.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_addresses_by_user(user_id: str, db: AsyncSession) -> List[Address]:
    result = await db.execute(
        select(Address).where(Address.user_id == user_id)
    )
    return result.scalars().all()


# ── FamilyMember ──────────────────────────────────────────────

async def get_family_member_by_id(member_id: str, user_id: str, db: AsyncSession) -> Optional[FamilyMember]:
    result = await db.execute(
        select(FamilyMember).where(
            FamilyMember.id == member_id,
            FamilyMember.user_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def get_family_members_by_user(user_id: str, db: AsyncSession) -> List[FamilyMember]:
    result = await db.execute(
        select(FamilyMember).where(FamilyMember.user_id == user_id)
    )
    return result.scalars().all()


# ── UserSession ───────────────────────────────────────────────

async def create_session(
    user_id: str,
    jti: str,
    device_info: Optional[str],
    ip_address: Optional[str],
    db: AsyncSession
) -> UserSession:
    """Called from auth module after login to record session."""
    session = UserSession(
        user_id=user_id,
        jti=jti,
        device_info=device_info,
        ip_address=ip_address,
        is_active=True,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_active_sessions(user_id: str, db: AsyncSession) -> List[UserSession]:
    result = await db.execute(
        select(UserSession).where(
            UserSession.user_id == user_id,
            UserSession.is_active == True
        ).order_by(UserSession.last_active.desc())
    )
    return result.scalars().all()


async def deactivate_session_by_jti(jti: str, db: AsyncSession) -> None:
    result = await db.execute(
        select(UserSession).where(UserSession.jti == jti)
    )
    session = result.scalar_one_or_none()
    if session:
        session.is_active = False
        await db.commit()
