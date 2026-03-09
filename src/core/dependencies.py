from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from src.api.deps.database import get_db
from jose import JWTError, jwt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

SECRET_KEY = "your-secret-key"   # must match LEV148's auth module
ALGORITHM = "HS256"

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    from src.models.user import User
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def require_partner(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from src.models.partner import Partner
    partner = db.query(Partner).filter(Partner.user_id == user.id).first()
    if not partner:
        raise HTTPException(status_code=403, detail="Partner profile not found")
    return user