"""
Middleware Module for API Gateway

Implements middleware components for request processing.
"""
from typing import Dict, Any, Callable, Awaitable
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        Process request and log details.

        Args:
            request: FastAPI request object
            call_next: Next middleware in chain

        Returns:
            Response object
        """
        start_time = time.time()

        response = await call_next(request)

        process_time = time.time() - start_time
        logger.info(
            f"{request.method} {request.url.path} "
            f"completed in {process_time:.3f}s"
        )

        return response

class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting request metrics."""

    def __init__(self, app):
        """Initialize the middleware."""
        super().__init__(app)
        self.request_count = 0
        self.error_count = 0

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        Process request and collect metrics.

        Args:
            request: FastAPI request object
            call_next: Next middleware in chain

        Returns:
            Response object
        """
        self.request_count += 1

        try:
            response = await call_next(request)
            if response.status_code >= 400:
                self.error_count += 1
            return response
        except Exception:
            self.error_count += 1
            raise

class SecurityMiddleware(BaseHTTPMiddleware):
    """Middleware for additional security measures."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        Process request and apply security measures.

        Args:
            request: FastAPI request object
            call_next: Next middleware in chain

        Returns:
            Response object
        """
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

        return response
