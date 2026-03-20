import time
import uuid
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("middleware")


class RequestLoggingMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        request.state.request_id = request_id

        response = await call_next(request)

        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            f"request_id={request_id} | "
            f"method={request.method} | "
            f"endpoint={request.url.path} | "
            f"status={response.status_code} | "
            f"duration={duration_ms:.2f}ms"
        )
        response.headers["X-Request-ID"] = request_id
        return response