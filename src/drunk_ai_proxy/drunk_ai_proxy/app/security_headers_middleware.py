"""Security headers middleware for FastAPI/Starlette applications.

Adds standard security headers to all HTTP responses to protect against
common web vulnerabilities like XSS, MIME sniffing, clickjacking, etc.
"""

from __future__ import annotations

from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all HTTP responses.

    Security headers help protect against:
    - MIME sniffing attacks: X-Content-Type-Options: nosniff
    - Clickjacking: X-Frame-Options: DENY
    - XSS attacks: X-XSS-Protection, Content-Security-Policy
    - Mixed content: Strict-Transport-Security
    - Sensitive information leakage: Referrer-Policy, Permissions-Policy

    Example:
        >>> from starlette.applications import Starlette
        >>> from starlette.middleware import Middleware
        >>> app = Starlette()
        >>> app.add_middleware(
        ...     SecurityHeadersMiddleware,
        ...     headers={
        ...         "X-Content-Type-Options": "nosniff",
        ...         "X-Frame-Options": "DENY",
        ...     }
        ... )
    """

    _DEFAULT_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    }

    def __init__(
        self,
        app: Any,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Initialize middleware with custom or default security headers.

        Args:
            app: The ASGI application.
            headers: Optional dict of custom headers to override defaults.
                    If provided, merged with defaults (custom overrides defaults).
        """
        super().__init__(app)
        self._headers = {**self._DEFAULT_HEADERS}
        if headers:
            self._headers.update(headers)

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Add security headers to response.

        Args:
            request: The HTTP request.
            call_next: Callable to pass to next middleware.

        Returns:
            Response with security headers added.
        """
        response = await call_next(request)

        # Add all configured security headers
        for header_name, header_value in self._headers.items():
            response.headers[header_name] = header_value

        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to limit request body size to prevent memory exhaustion attacks.

    Rejects requests with Content-Length exceeding the configured maximum.

    Example:
        >>> app = Starlette()
        >>> app.add_middleware(
        ...     RequestSizeLimitMiddleware,
        ...     max_size_bytes=10_242_880  # 10 MB
        ... )
    """

    def __init__(
        self,
        app: Any,
        max_size_bytes: int = 10 * 1024 * 1024,  # 10 MB default
    ) -> None:
        """Initialize middleware with size limit.

        Args:
            app: The ASGI application.
            max_size_bytes: Maximum allowed request size in bytes.
        """
        super().__init__(app)
        self._max_size_bytes = max_size_bytes

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Validate request size before processing.

        Args:
            request: The HTTP request.
            call_next: Callable to pass to next middleware.

        Returns:
            Response with error if size exceeded, or normal response.
        """
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                if size > self._max_size_bytes:
                    max_mb = self._max_size_bytes / (1024 * 1024)
                    return Response(
                        content=f"Request size exceeds {max_mb} MB limit",
                        status_code=413,  # Payload Too Large
                        media_type="text/plain",
                    )
            except (ValueError, TypeError):
                # Ignore unparseable content-length
                pass

        return await call_next(request)
