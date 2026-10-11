"""Request/response middleware for timing and logging."""

import time
import logging
import json
from datetime import datetime
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable

logger = logging.getLogger(__name__)


class TimingMiddleware(BaseHTTPMiddleware):
    """Middleware to track request/response times."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and add timing information.

        Args:
            request: The incoming request
            call_next: The next middleware/endpoint handler

        Returns:
            Response with timing header added
        """
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Add timing header
        response.headers["X-Process-Time"] = f"{duration_ms:.2f}ms"

        # Log request
        log_request(request, response, duration_ms)

        return response


class JSONLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured JSON logging of requests."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Log request and response in structured JSON format.

        Args:
            request: The incoming request
            call_next: The next middleware/endpoint handler

        Returns:
            Response from the endpoint
        """
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log in structured format
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent", "unknown")
        }

        # Log at appropriate level
        if response.status_code >= 500:
            logger.error(f"Request failed: {json.dumps(log_data)}")
        elif response.status_code >= 400:
            logger.warning(f"Client error: {json.dumps(log_data)}")
        else:
            logger.info(f"Request processed: {json.dumps(log_data)}")

        return response


def log_request(request: Request, response: Response, duration_ms: float) -> None:
    """
    Log request details in structured format.

    Args:
        request: The request object
        response: The response object
        duration_ms: Request duration in milliseconds
    """
    logger.info(
        "Request processed",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "client": request.client.host if request.client else None
        }
    )
