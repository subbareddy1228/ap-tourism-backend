# Users Module — Dev 2 Setup Guide

## Overview
Module 2 — Users API (/api/v1/user)
18 endpoints across 6 groups.
Owner: Dev 2
Depends on: Auth Module (Dev 1 — psubb)

---

## Files in This ZIP

| File | Location in Project |
|------|-------------------|
| user_profile.py | src/models/user_profile.py |
| user.py (schemas) | src/schemas/user.py |
| user_service.py | src/services/user_service.py |
| users.py (endpoints) | src/api/v1/endpoints/users.py |
| user_repo.py | src/repositories/user_repo.py |
| aws_s3.py | src/integrations/aws_s3.py |
| ALEMBIC_UPDATE.py | Read instructions inside |

---

## Setup Steps

### 1. Merge Auth Branch
```bash
git checkout feature/users
git merge origin/feature/auth
```

### 2. Copy Files
Place each file in the location shown above.

### 3. Update alembic/env.py
Open alembic/env.py and add after existing imports:
```python
from src.models.user_profile import UserProfile, Address, FamilyMember, UserSession
```

### 4. Update src/api/v1/router.py
Add users router:
```python
from src.api.v1.endpoints.users import router as users_router
api_router.include_router(users_router, prefix="/api/v1")
```

### 5. Add AWS S3 env variables to .env
```
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=ap-south-1
AWS_S3_BUCKET=ap-tourism-avatars
```

### 6. Add to src/core/config.py
```python
AWS_ACCESS_KEY_ID:     str = ""
AWS_SECRET_ACCESS_KEY: str = ""
AWS_REGION:            str = "ap-south-1"
AWS_S3_BUCKET:         str = "ap-tourism-avatars"
```

### 7. Run Migration
```bash
alembic revision --autogenerate -m "add users module tables"
alembic upgrade head
```

### 8. Start Server
```bash
python -m uvicorn src.main:app --port 8001
```

---

## Endpoints Summary

| Method | Endpoint | Auth Required |
|--------|----------|--------------|
| GET | /api/v1/user/me | ✅ |
| PUT | /api/v1/user/me | ✅ |
| PATCH | /api/v1/user/me/avatar | ✅ |
| DELETE | /api/v1/user/me | ✅ |
| GET | /api/v1/user/me/addresses | ✅ |
| POST | /api/v1/user/me/addresses | ✅ |
| PUT | /api/v1/user/me/addresses/{id} | ✅ |
| DELETE | /api/v1/user/me/addresses/{id} | ✅ |
| GET | /api/v1/user/me/family-members | ✅ |
| POST | /api/v1/user/me/family-members | ✅ |
| PUT | /api/v1/user/me/family-members/{id} | ✅ |
| DELETE | /api/v1/user/me/family-members/{id} | ✅ |
| POST | /api/v1/user/me/verify-phone | ✅ |
| POST | /api/v1/user/me/verify-phone/confirm | ✅ |
| GET | /api/v1/user/me/preferences | ✅ |
| PUT | /api/v1/user/me/preferences | ✅ |
| GET | /api/v1/user/me/sessions | ✅ |
| DELETE | /api/v1/user/me/sessions/{id} | ✅ |

---

## Important Rules

- DO NOT edit src/models/user.py — coordinate with Dev 1 (psubb)
- DO NOT edit src/api/deps/auth.py — use it, don't modify it
- Only edit files in your module folder
- Always use get_current_user from src.api.deps.auth
