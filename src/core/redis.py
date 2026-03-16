import redis as redis_lib
from src.core.config import settings


def get_redis():
    client = None
    try:
        client = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
        client.ping()
    except Exception:
        client = None

    try:
        yield client
    finally:
        if client:
            try:
                client.close()
            except Exception:
                pass