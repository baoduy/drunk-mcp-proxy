"""Security headers middleware for FastAPI/Starlette applications."""

from __future__ import annotations

from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all HTTP responses."""

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
        super().__init__(app)
        self._headers = {**self._DEFAULT_HEADERS}
        if headers:
            self._headers.update(headers)

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        response = await call_next(request)

        for header_name, header_value in self._headers.items():
            response.headers[header_name] = header_value

        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to limit request body size to prevent memory exhaustion attacks."""

    def __init__(
        self,
        app: Any,
        max_size_bytes: int = 10 * 1024 * 1024,
    ) -> None:
        super().__init__(app)
        self._max_size_bytes = max_size_bytes

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                if size > self._max_size_bytes:
                    max_mb = self._max_size_bytes / (1024 * 1024)
                    return Response(
                        content=f"Request size exceeds {max_mb} MB limit",
                        status_code=413,
                        media_type="text/plain",
                    )
            except (ValueError, TypeError):
                pass

        return await call_next(request)
