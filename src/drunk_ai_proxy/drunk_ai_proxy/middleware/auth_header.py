"""Authorization header enforcement middleware."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse

from drunk_ai_proxy.utils.auth_header_policy import DEFAULT_ANONYMOUS_PATHS, is_anonymous_path


class AuthHeaderMiddleware(BaseHTTPMiddleware):
    """Validate that non-anonymous requests include an Authorization header."""

    _AnonymousPaths = DEFAULT_ANONYMOUS_PATHS

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        if is_anonymous_path(request.url.path, self._AnonymousPaths):
            return await call_next(request)

        authorization = request.headers.get("authorization", "").strip()
        if not authorization:
            return JSONResponse(
                status_code=401,
                content={"error": "Missing or empty Authorization header"},
            )

        return await call_next(request)
