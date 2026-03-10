from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from uuid import UUID
from dataclasses import dataclass
from src.core.security import decode_access_token

bearer_scheme = HTTPBearer()


@dataclass
class CurrentUser:
    id: UUID
    role: str


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> CurrentUser:
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        user_id: str = payload.get("sub")
        role: str = payload.get("role", "user")
        if not user_id:
            raise ValueError("Missing sub")
        return CurrentUser(id=UUID(user_id), role=role)
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )