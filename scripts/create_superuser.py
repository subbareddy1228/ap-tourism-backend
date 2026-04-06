"""
scripts/create_superuser.py
Create the first admin user for AP Tourism backend.

Usage:
    python scripts/create_superuser.py
    python scripts/create_superuser.py --phone 9876543210 --name "Super Admin"
"""

import asyncio
import argparse
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select

from src.core.config import settings
from src.core.security import hash_password
from src.models.user import User
from src.models.user_profile import UserProfile
from src.common.enums import UserRole, UserStatus


async def create_superuser(phone: str, name: str, password: str):
    """Create admin user in the database."""

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with SessionLocal() as db:
        # Check if user already exists
        result = await db.execute(select(User).where(User.phone == phone))
        existing = result.scalar_one_or_none()

        if existing:
            if existing.role.value == "admin":
                print(f"✅ Admin user with phone {phone} already exists.")
            else:
                existing.role   = UserRole.ADMIN
                existing.status = UserStatus.ACTIVE
                existing.is_phone_verified = True
                if password:
                    existing.password_hash = hash_password(password)
                await db.commit()
                print(f"✅ User {phone} upgraded to admin.")
            return

        # Create new admin user
        user = User(
            phone             = phone,
            full_name         = name,
            password_hash     = hash_password(password) if password else None,
            role              = UserRole.ADMIN,
            status            = UserStatus.ACTIVE,
            is_phone_verified = True,
            is_email_verified = False,
        )
        db.add(user)
        await db.flush()

        # Create profile
        profile = UserProfile(
        user_id     = user.id,
        language    = "en",
        kyc_status  = "pending",
        preferences = {},
    )
        db.add(profile)
        await db.commit()

        print(f"✅ Admin user created!")
        print(f"   Phone:    {phone}")
        print(f"   Name:     {name}")
        print(f"   Role:     admin")
        print(f"   Password: {'set' if password else 'not set (OTP login only)'}")
        print(f"   ID:       {user.id}")

    await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description="Create AP Tourism superuser")
    parser.add_argument("--phone",    default="9999999999",  help="Phone number (default: 9999999999)")
    parser.add_argument("--name",     default="Super Admin", help="Full name (default: Super Admin)")
    parser.add_argument("--password", default="Admin@123",   help="Password (default: Admin@123)")
    args = parser.parse_args()

    print(f"Creating superuser...")
    print(f"Phone: {args.phone}")
    print(f"Name:  {args.name}")
    print()

    asyncio.run(create_superuser(
        phone=args.phone,
        name=args.name,
        password=args.password,
    ))


if __name__ == "__main__":
    main()