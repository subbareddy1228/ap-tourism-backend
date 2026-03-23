from jose import jwt
from datetime import datetime, timedelta

SECRET_KEY = "change-this-secret-key"
ALGORITHM = "HS256"

payload = {
    "sub": "550e8400-e29b-41d4-a716-446655440000",
    "exp": datetime.utcnow() + timedelta(hours=24)
}
token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
print(token)
