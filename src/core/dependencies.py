from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from uuid import UUID
from dataclasses import dataclass
from typing import Optional

from src.core.config import settings
from src.core.database import get_db

bearer_scheme = HTTPBearer()


@dataclass
class TokenUser:
    id: UUID
    email: str
    role: str  # "user" | "admin" | "guide"


def decode_token(token: str) -> TokenUser:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        email: str = payload.get("email", "")
        role: str = payload.get("role", "user")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload.")
        return TokenUser(id=UUID(user_id), email=email, role=role)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid or expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> TokenUser:
    return decode_token(credentials.credentials)


def get_admin_user(
    current_user: TokenUser = Depends(get_current_user),
) -> TokenUser:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return current_user
