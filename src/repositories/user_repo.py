
"""
repositories/user_repo.py
All database queries for User, UserProfile, UserAddress, FamilyMember, SavedItem.
Uses AsyncSession — same pattern as auth_service.
"""

from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_

from src.models.user import User
from src.models.user_profile import UserProfile, UserAddress, FamilyMember, SavedItem
from src.common.responses import UserRole, UserStatus


# ═══════════════════════════════════════════════════════════════
# USER QUERIES
# ═══════════════════════════════════════════════════════════════

async def get_user_by_id(db: AsyncSession, user_id: UUID) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id, User.deleted_at.is_(None)))
    return result.scalar_one_or_none()


async def get_user_by_phone(db: AsyncSession, phone: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.phone == phone, User.deleted_at.is_(None)))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email, User.deleted_at.is_(None)))
    return result.scalar_one_or_none()


async def update_user_fields(db: AsyncSession, user_id: UUID, **fields) -> Optional[User]:
    """Generic update for User table fields (email, full_name, status, etc.)."""
    fields["updated_at"] = datetime.utcnow()
    await db.execute(
        update(User).where(User.id == user_id).values(**fields)
    )
    await db.commit()
    return await get_user_by_id(db, user_id)


async def soft_delete_user(db: AsyncSession, user_id: UUID) -> None:
    """Soft-delete: sets deleted_at timestamp and status=deleted."""
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(deleted_at=datetime.utcnow(), status=UserStatus.DELETED)
    )
    await db.commit()


async def list_users(
    db: AsyncSession,
    page: int = 1,
    limit: int = 20,
    role: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> Tuple[List[User], int]:
    """Admin: paginated user list with optional filters."""
    query = select(User).where(User.deleted_at.is_(None))

    if role:
        query = query.where(User.role == role)
    if status:
        query = query.where(User.status == status)
    if search:
        query = query.where(
            or_(
                User.full_name.ilike(f"%{search}%"),
                User.phone.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
            )
        )

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(User.created_at.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    return result.scalars().all(), total


# ═══════════════════════════════════════════════════════════════
# PROFILE QUERIES
# ═══════════════════════════════════════════════════════════════

async def get_profile_by_user_id(db: AsyncSession, user_id: UUID) -> Optional[UserProfile]:
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def create_profile(db: AsyncSession, user_id: UUID) -> UserProfile:
    """Auto-create profile when user first accesses it."""
    profile = UserProfile(user_id=user_id)
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


async def get_or_create_profile(db: AsyncSession, user_id: UUID) -> UserProfile:
    profile = await get_profile_by_user_id(db, user_id)
    if not profile:
        profile = await create_profile(db, user_id)
    return profile


async def update_profile_fields(db: AsyncSession, user_id: UUID, **fields) -> UserProfile:
    fields["updated_at"] = datetime.utcnow()
    await db.execute(
        update(UserProfile).where(UserProfile.user_id == user_id).values(**fields)
    )
    await db.commit()
    return await get_profile_by_user_id(db, user_id)


async def check_profile_completeness(profile: UserProfile, user: User) -> bool:
    """Returns True if profile has all key fields filled."""
    return all([
        user.full_name,
        user.email,
        profile.gender,
        profile.date_of_birth,
        profile.emergency_contact_name,
        profile.emergency_contact_phone,
    ])


# ═══════════════════════════════════════════════════════════════
# ADDRESS QUERIES
# ═══════════════════════════════════════════════════════════════

async def get_addresses(db: AsyncSession, profile_id: UUID) -> List[UserAddress]:
    result = await db.execute(
        select(UserAddress)
        .where(UserAddress.profile_id == profile_id)
        .order_by(UserAddress.is_default.desc(), UserAddress.created_at)
    )
    return result.scalars().all()


async def get_address_by_id(db: AsyncSession, address_id: UUID, profile_id: UUID) -> Optional[UserAddress]:
    result = await db.execute(
        select(UserAddress).where(
            UserAddress.id == address_id,
            UserAddress.profile_id == profile_id
        )
    )
    return result.scalar_one_or_none()


async def create_address(db: AsyncSession, profile_id: UUID, data: dict) -> UserAddress:
    # If new address is_default, clear other defaults first
    if data.get("is_default"):
        await db.execute(
            update(UserAddress)
            .where(UserAddress.profile_id == profile_id)
            .values(is_default=False)
        )
    address = UserAddress(profile_id=profile_id, **data)
    db.add(address)
    await db.commit()
    await db.refresh(address)
    return address


async def update_address(db: AsyncSession, address_id: UUID, profile_id: UUID, data: dict) -> Optional[UserAddress]:
    if data.get("is_default"):
        await db.execute(
            update(UserAddress)
            .where(UserAddress.profile_id == profile_id)
            .values(is_default=False)
        )
    await db.execute(
        update(UserAddress)
        .where(UserAddress.id == address_id, UserAddress.profile_id == profile_id)
        .values(**data)
    )
    await db.commit()
    return await get_address_by_id(db, address_id, profile_id)


async def delete_address(db: AsyncSession, address_id: UUID, profile_id: UUID) -> bool:
    result = await db.execute(
        delete(UserAddress).where(
            UserAddress.id == address_id,
            UserAddress.profile_id == profile_id
        )
    )
    await db.commit()
    return result.rowcount > 0


async def set_default_address(db: AsyncSession, address_id: UUID, profile_id: UUID) -> Optional[UserAddress]:
    await db.execute(
        update(UserAddress)
        .where(UserAddress.profile_id == profile_id)
        .values(is_default=False)
    )
    await db.execute(
        update(UserAddress)
        .where(UserAddress.id == address_id, UserAddress.profile_id == profile_id)
        .values(is_default=True)
    )
    await db.commit()
    return await get_address_by_id(db, address_id, profile_id)


# ═══════════════════════════════════════════════════════════════
# FAMILY MEMBER QUERIES
# ═══════════════════════════════════════════════════════════════

async def get_family_members(db: AsyncSession, profile_id: UUID) -> List[FamilyMember]:
    result = await db.execute(
        select(FamilyMember)
        .where(FamilyMember.profile_id == profile_id)
        .order_by(FamilyMember.created_at)
    )
    return result.scalars().all()


async def get_family_member_by_id(db: AsyncSession, member_id: UUID, profile_id: UUID) -> Optional[FamilyMember]:
    result = await db.execute(
        select(FamilyMember).where(
            FamilyMember.id == member_id,
            FamilyMember.profile_id == profile_id
        )
    )
    return result.scalar_one_or_none()


async def create_family_member(db: AsyncSession, profile_id: UUID, data: dict) -> FamilyMember:
    member = FamilyMember(profile_id=profile_id, **data)
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return member


async def update_family_member(db: AsyncSession, member_id: UUID, profile_id: UUID, data: dict) -> Optional[FamilyMember]:
    await db.execute(
        update(FamilyMember)
        .where(FamilyMember.id == member_id, FamilyMember.profile_id == profile_id)
        .values(**data)
    )
    await db.commit()
    return await get_family_member_by_id(db, member_id, profile_id)


async def delete_family_member(db: AsyncSession, member_id: UUID, profile_id: UUID) -> bool:
    result = await db.execute(
        delete(FamilyMember).where(
            FamilyMember.id == member_id,
            FamilyMember.profile_id == profile_id
        )
    )
    await db.commit()
    return result.rowcount > 0


# ═══════════════════════════════════════════════════════════════
# SAVED ITEMS QUERIES
# ═══════════════════════════════════════════════════════════════

async def get_saved_items(
    db: AsyncSession,
    profile_id: UUID,
    item_type: Optional[str] = None,
    page: int = 1,
    limit: int = 20
) -> Tuple[List[SavedItem], int]:
    query = select(SavedItem).where(SavedItem.profile_id == profile_id)
    if item_type:
        query = query.where(SavedItem.item_type == item_type)

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar_one()

    query = query.order_by(SavedItem.saved_at.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    return result.scalars().all(), total


async def save_item(db: AsyncSession, profile_id: UUID, item_id: UUID, item_type: str) -> SavedItem:
    # Check if already saved
    existing = await db.execute(
        select(SavedItem).where(
            SavedItem.profile_id == profile_id,
            SavedItem.item_id == item_id,
            SavedItem.item_type == item_type
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("Item already saved")

    item = SavedItem(profile_id=profile_id, item_id=item_id, item_type=item_type)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def unsave_item(db: AsyncSession, profile_id: UUID, item_id: UUID) -> bool:
    result = await db.execute(
        delete(SavedItem).where(
            SavedItem.profile_id == profile_id,
            SavedItem.item_id == item_id
        )
    )
    await db.commit()
    return result.rowcount > 0


# ═══════════════════════════════════════════════════════════════
# LOYALTY HELPERS
# ═══════════════════════════════════════════════════════════════

def get_loyalty_tier(points: int) -> str:
    if points >= 10000: return "platinum"
    if points >= 5000:  return "gold"
    if points >= 1000:  return "silver"
    return "bronze"


async def add_loyalty_points(db: AsyncSession, user_id: UUID, points: int) -> UserProfile:
    profile = await get_or_create_profile(db, user_id)
    await db.execute(
        update(UserProfile)
        .where(UserProfile.user_id == user_id)
        .values(loyalty_points=UserProfile.loyalty_points + points)
    )
    await db.commit()
    return await get_profile_by_user_id(db, user_id)
