import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.core.database import get_db

# Fake database dependency
async def override_get_db():
    yield None

# Override DB dependency
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c