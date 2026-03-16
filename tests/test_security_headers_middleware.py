"""Tests for security headers middleware."""

from __future__ import annotations

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
from starlette.testclient import TestClient

from drunk_ai_proxy.app.security_headers_middleware import (
    SecurityHeadersMiddleware,
    RequestSizeLimitMiddleware,
)


class TestSecurityHeadersMiddleware:
    """Test security headers middleware."""

    def test_default_headers_added(self) -> None:
        """Default security headers are added to responses."""
        app = Starlette()
        app.add_middleware(SecurityHeadersMiddleware)

        @app.route("/test")
        def test_endpoint(request: Request) -> Response:
            return Response("OK")

        client = TestClient(app)
        response = client.get("/test")

        # Check default headers are present
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert "Strict-Transport-Security" in response.headers
        assert "Referrer-Policy" in response.headers
        assert "Permissions-Policy" in response.headers

    def test_custom_headers_override_defaults(self) -> None:
        """Custom headers override defaults."""
        app = Starlette()
        app.add_middleware(
            SecurityHeadersMiddleware,
            headers={"X-Frame-Options": "SAMEORIGIN"},
        )

        @app.route("/test")
        def test_endpoint(request: Request) -> Response:
            return Response("OK")

        client = TestClient(app)
        response = client.get("/test")

        # Custom header overrides default
        assert response.headers["X-Frame-Options"] == "SAMEORIGIN"
        # Default headers still present
        assert response.headers["X-Content-Type-Options"] == "nosniff"

    def test_csp_header_added(self) -> None:
        """Content-Security-Policy header can be configured."""
        app = Starlette()
        app.add_middleware(
            SecurityHeadersMiddleware,
            headers={
                "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'",
            },
        )

        @app.route("/test")
        def test_endpoint(request: Request) -> Response:
            return Response("OK")

        client = TestClient(app)
        response = client.get("/test")

        assert "Content-Security-Policy" in response.headers


class TestRequestSizeLimitMiddleware:
    """Test request size limit middleware."""

    def test_small_request_accepted(self) -> None:
        """Requests under limit are accepted."""
        app = Starlette()
        app.add_middleware(RequestSizeLimitMiddleware, max_size_bytes=1000)

        @app.route("/test", methods=["POST"])
        def test_endpoint(request: Request) -> Response:
            return Response("OK")

        client = TestClient(app)
        response = client.post(
            "/test",
            content="x" * 500,
        )
        assert response.status_code == 200

    def test_large_request_rejected(self) -> None:
        """Requests exceeding limit are rejected."""
        app = Starlette()
        app.add_middleware(RequestSizeLimitMiddleware, max_size_bytes=1000)

        @app.route("/test", methods=["POST"])
        def test_endpoint(request: Request) -> Response:
            return Response("OK")

        client = TestClient(app)
        response = client.post(
            "/test",
            content="x" * 5000,
        )
        assert response.status_code == 413

    def test_default_10mb_limit(self) -> None:
        """Default limit is 10MB."""
        app = Starlette()
        app.add_middleware(RequestSizeLimitMiddleware)

        @app.route("/test", methods=["POST"])
        def test_endpoint(request: Request) -> Response:
            return Response("OK")

        client = TestClient(app)
        # Small request well under 10MB
        response = client.post(
            "/test",
            content="x" * 1000,
        )
        assert response.status_code == 200
