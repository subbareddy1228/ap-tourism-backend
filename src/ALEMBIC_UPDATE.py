"""
alembic/env.py
Updated to include Users Module models.
Add these imports AFTER the existing auth model imports.

INSTRUCTIONS FOR DEV 2:
Open your alembic/env.py and add these lines after the existing imports:
"""

# ── EXISTING (from Dev 1 — DO NOT REMOVE) ────────────────────
from src.models.user import User          # noqa: F401

# ── ADD THESE (Dev 2 — Users Module) ─────────────────────────
from src.models.user_profile import (     # noqa: F401
    UserProfile,
    Address,
    FamilyMember,
    UserSession,
)

# ── After adding imports, run: ────────────────────────────────
# alembic revision --autogenerate -m "add users module tables"
# alembic upgrade head
