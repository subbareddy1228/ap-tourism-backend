from fastapi import Depends, HTTPException, status
from src.api.deps.auth import get_current_user, CurrentUser


def require_admin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user