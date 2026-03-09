# ============================================================
# app/dependencies.py
# Auth Dependencies — shared across all modules
# (Created by LEV148 - Perumalla Subbarao, Auth team)
# ============================================================

import os
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.models.user import User

SECRET_KEY  = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM   = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db:    Session = Depends(get_db)
) -> User:
    """
    Decode JWT token and return the logged-in User object.
    Raises 401 if token is missing, invalid, or expired.
    Raises 401 if user is deleted or inactive.
    Usage: current_user: User = Depends(get_current_user)
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise credentials_exception

    if user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This account has been deleted"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is suspended. Please contact support."
        )

    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Same as get_current_user but ALSO checks admin role.
    Raises 403 if user is not ADMIN.
    Usage: admin_user: User = Depends(require_admin)
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user
