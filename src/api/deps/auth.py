from typing import Optional
 
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
 
from src.core.config import settings
 
bearer_scheme = HTTPBearer(auto_error=False)
 
 
def _decode_token(token: str) -> dict:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
        )
 
 
async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str:                                              # ← was int, now str
    """
    Dependency that extracts the user_id from the JWT bearer token.
    Raises 401 if token is missing or invalid.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization token required.",
        )
    payload = _decode_token(credentials.credentials)
    user_id = payload.get("sub")                       # ← only read "sub" (UUID string)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token does not contain a valid user_id.",
        )
    return str(user_id)                                # ← return as str, not int
 
 
async def get_optional_user_id(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> Optional[str]:                                    # ← was Optional[int], now Optional[str]
    """
    Dependency that optionally extracts user_id from JWT.
    Returns None if no token provided — used for public endpoints
    that optionally track the user (e.g. global search history).
    """
    if credentials is None:
        return None
    try:
        payload = _decode_token(credentials.credentials)
        user_id = payload.get("sub")                   # ← only read "sub" (UUID string)
        return str(user_id) if user_id is not None else None  # ← return as str, not int
    except HTTPException:
        return None
