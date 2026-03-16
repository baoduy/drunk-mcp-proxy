"""
Unit tests for src/app/middleware_provider module.

Tests middleware initialization and configuration.
"""

import asyncio
import pytest
from unittest.mock import patch, AsyncMock, Mock
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.testclient import TestClient
from fastapi import FastAPI
from drunk_ai_proxy.app import middleware_provider
from drunk_ai_proxy.app.middleware_provider import AuthHeaderMiddleware, RateLimitMiddleware


class TestParseCsv:
    """Test suite for MiddlewareProvider._parse_csv static method."""

    def test_parse_csv_simple(self):
        """Test parsing simple comma-separated values."""
        result = middleware_provider.MiddlewareProvider._parse_csv("a,b,c")
        assert result == ["a", "b", "c"]

    def test_parse_csv_with_spaces(self):
        """Test parsing CSV with spaces around values."""
        result = middleware_provider.MiddlewareProvider._parse_csv("a, b , c")
        assert result == ["a", "b", "c"]

    def test_parse_csv_empty_string(self):
        """Test parsing empty string returns empty list."""
        result = middleware_provider.MiddlewareProvider._parse_csv("")
        assert result == []

    def test_parse_csv_with_empty_items(self):
        """Test parsing CSV filters out empty items."""
        result = middleware_provider.MiddlewareProvider._parse_csv("a,,b,")
        assert result == ["a", "b"]

    def test_parse_csv_single_item(self):
        """Test parsing single item."""
        result = middleware_provider.MiddlewareProvider._parse_csv("single")
        assert result == ["single"]

    def test_parse_csv_whitespace_only(self):
        """Test parsing whitespace-only string returns empty list."""
        result = middleware_provider.MiddlewareProvider._parse_csv("   ")
        assert result == []

    def test_parse_csv_empty_fallback(self):
        """Test parsing empty string as fallback returns empty list."""
        result = middleware_provider.MiddlewareProvider._parse_csv("")
        assert result == []


class TestBuildCorsMiddleware:
    """Test suite for build_cors_middleware function."""

    @patch('drunk_ai_proxy.app.middleware_provider.CORS_ALLOW_ORIGINS', '')
    @patch('drunk_ai_proxy.app.middleware_provider.CORS_ALLOW_METHODS', '')
    @patch('drunk_ai_proxy.app.middleware_provider.CORS_ALLOW_HEADERS', '')
    @patch('drunk_ai_proxy.app.middleware_provider.CORS_EXPOSE_HEADERS', '')
    def test_build_cors_middleware_disabled(self):
        """Test CORS middleware with default values when origins not set."""
        result = middleware_provider.MiddlewareProvider(Mock())._create_cors_middleware()
        assert result is not None
        assert isinstance(result, Middleware)
        assert result.kwargs['allow_origins'] == ['*']  # Defaults to allow all
        assert result.kwargs['allow_methods'] == ['*']
        assert result.kwargs['allow_headers'] == ['*']

    @patch('drunk_ai_proxy.app.middleware_provider.CORS_ALLOW_ORIGINS', 'https://example.com')
    @patch('drunk_ai_proxy.app.middleware_provider.CORS_ALLOW_METHODS', '')
    @patch('drunk_ai_proxy.app.middleware_provider.CORS_ALLOW_HEADERS', '')
    @patch('drunk_ai_proxy.app.middleware_provider.CORS_EXPOSE_HEADERS', '')
    def test_build_cors_middleware_with_origin(self):
        """Test CORS middleware is built with single origin."""
        result = middleware_provider.MiddlewareProvider(Mock())._create_cors_middleware()
        
        assert result is not None
        assert isinstance(result, Middleware)
        assert result.cls == CORSMiddleware
        assert result.kwargs['allow_origins'] == ['https://example.com']
        assert result.kwargs['allow_methods'] == ['*']
        assert result.kwargs['allow_headers'] == ['*']

    @patch('drunk_ai_proxy.app.middleware_provider.CORS_ALLOW_ORIGINS', 'https://example.com,https://app.example.com')
    @patch('drunk_ai_proxy.app.middleware_provider.CORS_ALLOW_METHODS', 'GET,POST,PUT')
    @patch('drunk_ai_proxy.app.middleware_provider.CORS_ALLOW_HEADERS', 'Content-Type,Authorization')
    @patch('drunk_ai_proxy.app.middleware_provider.CORS_EXPOSE_HEADERS', 'X-Request-ID')
    def test_build_cors_middleware_all_options(self):
        """Test CORS middleware with all options configured."""
        result = middleware_provider.MiddlewareProvider(Mock())._create_cors_middleware()
        
        assert result is not None
        assert result.kwargs['allow_origins'] == ['https://example.com', 'https://app.example.com']
        assert result.kwargs['allow_methods'] == ['GET', 'POST', 'PUT']
        assert result.kwargs['allow_headers'] == ['Content-Type', 'Authorization']
        assert result.kwargs['expose_headers'] == ['X-Request-ID']

    @patch('drunk_ai_proxy.app.middleware_provider.CORS_ALLOW_ORIGINS', '  https://example.com  ')
    @patch('drunk_ai_proxy.app.middleware_provider.CORS_ALLOW_METHODS', '')
    @patch('drunk_ai_proxy.app.middleware_provider.CORS_ALLOW_HEADERS', '')
    @patch('drunk_ai_proxy.app.middleware_provider.CORS_EXPOSE_HEADERS', '')
    def test_build_cors_middleware_strips_whitespace(self):
        """Test CORS middleware strips whitespace from values."""
        result = middleware_provider.MiddlewareProvider(Mock())._create_cors_middleware()
        
        assert result is not None
        assert result.kwargs['allow_origins'] == ['https://example.com']


class TestMiddlewareProviderBuild:
    """Test suite for MiddlewareProvider.build() method."""

    @patch('drunk_ai_proxy.app.middleware_provider.RATE_LIMIT_ENABLED', False)
    def test_build_with_core_middlewares(self):
        """Test build includes CORS, request-size, and security-headers middleware."""
        provider = middleware_provider.MiddlewareProvider(cache=Mock())
        mock_cors = Middleware(CORSMiddleware, allow_origins=['*'])
        mock_size = Middleware(CORSMiddleware, allow_origins=['*'])
        mock_sec = Middleware(CORSMiddleware, allow_origins=['*'])
        provider._create_cors_middleware = lambda: mock_cors
        provider._create_request_size_limit_middleware = lambda: mock_size
        provider._create_security_headers_middleware = lambda: mock_sec

        result = provider.build()

        assert len(result) == 3
        assert result[0] == mock_cors
        assert result[1] == mock_size
        assert result[2] == mock_sec

    @patch('drunk_ai_proxy.app.middleware_provider.RATE_LIMIT_ENABLED', False)
    def test_build_with_none_cors_still_includes_slot(self):
        """Test build still returns list when CORS middleware factory returns None."""
        provider = middleware_provider.MiddlewareProvider(cache=Mock())
        mock_size = Middleware(CORSMiddleware, allow_origins=['*'])
        mock_sec = Middleware(CORSMiddleware, allow_origins=['*'])
        provider._create_cors_middleware = lambda: None
        provider._create_request_size_limit_middleware = lambda: mock_size
        provider._create_security_headers_middleware = lambda: mock_sec

        result = provider.build()

        assert len(result) == 3
        assert result[0] is None
        assert result[1] == mock_size
        assert result[2] == mock_sec

    @patch('drunk_ai_proxy.app.middleware_provider.RATE_LIMIT_ENABLED', False)
    def test_build_returns_list(self):
        """Test build always returns a list."""
        provider = middleware_provider.MiddlewareProvider(cache=Mock())
        provider._create_cors_middleware = lambda: []
        provider._create_request_size_limit_middleware = lambda: []
        provider._create_security_headers_middleware = lambda: []

        result = provider.build()

        assert isinstance(result, list)

    @patch('drunk_ai_proxy.app.middleware_provider.RATE_LIMIT_ENABLED', True)
    def test_build_includes_rate_limit_when_enabled(self):
        """Test build appends rate limit middleware when RATE_LIMIT_ENABLED is True."""
        provider = middleware_provider.MiddlewareProvider(cache=Mock())
        mock_cors = Middleware(CORSMiddleware, allow_origins=['*'])
        mock_size = Middleware(CORSMiddleware, allow_origins=['*'])
        mock_sec = Middleware(CORSMiddleware, allow_origins=['*'])
        mock_rate = Middleware(CORSMiddleware, allow_origins=['*'])
        provider._create_cors_middleware = lambda: mock_cors
        provider._create_request_size_limit_middleware = lambda: mock_size
        provider._create_security_headers_middleware = lambda: mock_sec
        provider._create_rate_limit_middleware = lambda: mock_rate

        result = provider.build()

        assert len(result) == 4
        assert result[0] == mock_cors
        assert result[1] == mock_size
        assert result[2] == mock_sec
        assert result[3] == mock_rate

class TestAuthHeaderMiddleware:
    """Tests for AuthHeaderMiddleware dispatch logic."""

    @pytest.mark.asyncio
    async def test_auth_middleware_allows_anonymous_path(self) -> None:
        """Allow requests to anonymous paths without auth."""
        middleware = AuthHeaderMiddleware(AsyncMock())
        request = Mock(spec=Request)
        request.url = Mock(path="/health")
        request.headers = {}
        
        call_next = AsyncMock(return_value="response")
        result = await middleware.dispatch(request, call_next)
        
        assert result == "response"
        call_next.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_auth_middleware_rejects_missing_header(self) -> None:
        """Reject request with missing Authorization header."""
        middleware = AuthHeaderMiddleware(AsyncMock())
        request = Mock(spec=Request)
        request.url = Mock(path="/api/test")
        request.headers = {}
        
        call_next = AsyncMock()
        result = await middleware.dispatch(request, call_next)
        
        assert result.status_code == 401
        assert "Authorization" in result.body.decode()
        call_next.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_auth_middleware_rejects_empty_header(self) -> None:
        """Reject request with empty Authorization header."""
        middleware = AuthHeaderMiddleware(AsyncMock())
        request = Mock(spec=Request)
        request.url = Mock(path="/api/test")
        request.headers = {"authorization": "   "}
        
        call_next = AsyncMock()
        result = await middleware.dispatch(request, call_next)
        
        assert result.status_code == 401
        call_next.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_auth_middleware_allows_valid_header(self) -> None:
        """Allow request with valid Authorization header."""
        middleware = AuthHeaderMiddleware(AsyncMock())
        request = Mock(spec=Request)
        request.url = Mock(path="/api/test")
        request.headers = {"authorization": "Bearer token123"}
        
        call_next = AsyncMock(return_value="response")
        result = await middleware.dispatch(request, call_next)
        
        assert result == "response"
        call_next.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_auth_middleware_header_case_insensitive(self) -> None:
        """Handle Authorization header case-insensitively (Starlette normalizes)."""
        middleware = AuthHeaderMiddleware(AsyncMock())
        request = Mock(spec=Request)
        request.url = Mock(path="/api/test")
        # Starlette normalizes headers to lowercase in actual requests
        request.headers = {"authorization": "Bearer token123"}
        
        call_next = AsyncMock(return_value="response")
        result = await middleware.dispatch(request, call_next)
        
        assert result == "response"


class TestGetClientIP:
    """Tests for _get_client_ip helper."""

    def test_get_client_ip_from_x_forwarded_for(self) -> None:
        """Extract first IP from x-forwarded-for header."""
        request = Mock(spec=Request)
        request.headers = {"x-forwarded-for": "192.168.1.1, 10.0.0.1"}
        request.client = None
        
        ip = RateLimitMiddleware._get_client_ip(request)
        assert ip == "192.168.1.1"

    def test_get_client_ip_from_x_forwarded_for_single(self) -> None:
        """Handle single IP in x-forwarded-for."""
        request = Mock(spec=Request)
        request.headers = {"x-forwarded-for": "192.168.1.1"}
        request.client = None
        
        ip = RateLimitMiddleware._get_client_ip(request)
        assert ip == "192.168.1.1"

    def test_get_client_ip_from_x_forwarded_for_with_spaces(self) -> None:
        """Trim whitespace from x-forwarded-for."""
        request = Mock(spec=Request)
        request.headers = {"x-forwarded-for": "  192.168.1.1  ,  10.0.0.1  "}
        request.client = None
        
        ip = RateLimitMiddleware._get_client_ip(request)
        assert ip == "192.168.1.1"

    def test_get_client_ip_from_x_forwarded_for_empty_items(self) -> None:
        """Skip empty items in x-forwarded-for."""
        request = Mock(spec=Request)
        request.headers = {"x-forwarded-for": "192.168.1.1,,10.0.0.1"}
        request.client = None
        
        ip = RateLimitMiddleware._get_client_ip(request)
        assert ip == "192.168.1.1"

    def test_get_client_ip_fallback_to_request_client(self) -> None:
        """Fall back to request.client when x-forwarded-for missing."""
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="10.0.0.5")
        
        ip = RateLimitMiddleware._get_client_ip(request)
        assert ip == "10.0.0.5"

    def test_get_client_ip_fallback_to_unknown(self) -> None:
        """Use 'unknown' when IP sources unavailable."""
        request = Mock(spec=Request)
        request.headers = {}
        request.client = None
        
        ip = RateLimitMiddleware._get_client_ip(request)
        assert ip == "unknown"

    def test_get_client_ip_x_forwarded_for_takes_priority(self) -> None:
        """x-forwarded-for takes priority over request.client."""
        request = Mock(spec=Request)
        request.headers = {"x-forwarded-for": "192.168.1.1"}
        request.client = Mock(host="10.0.0.5")
        
        ip = RateLimitMiddleware._get_client_ip(request)
        assert ip == "192.168.1.1"

    def test_get_client_ip_empty_x_forwarded_for(self) -> None:
        """Handle empty x-forwarded-for header."""
        request = Mock(spec=Request)
        request.headers = {"x-forwarded-for": ""}
        request.client = Mock(host="10.0.0.5")
        
        ip = RateLimitMiddleware._get_client_ip(request)
        assert ip == "10.0.0.5"


class TestRateLimitMiddleware:
    """Tests for RateLimitMiddleware dispatch logic."""

    @patch("drunk_ai_proxy.app.middleware_provider.RATE_LIMIT_REQUESTS", 0)
    @patch("drunk_ai_proxy.app.middleware_provider.RATE_LIMIT_WINDOW_SECONDS", 60)
    def test_create_rate_limit_middleware_raises_for_zero_max_requests(self) -> None:
        """Raise ValueError when RATE_LIMIT_ENABLED is true and max requests is invalid."""
        with pytest.raises(
            ValueError,
            match="RATE_LIMIT_REQUESTS and RATE_LIMIT_WINDOW_SECONDS must be greater than 0",
        ):
            middleware_provider.MiddlewareProvider(Mock())._create_rate_limit_middleware()

    @patch("drunk_ai_proxy.app.middleware_provider.RATE_LIMIT_REQUESTS", 10)
    @patch("drunk_ai_proxy.app.middleware_provider.RATE_LIMIT_WINDOW_SECONDS", 0)
    def test_create_rate_limit_middleware_raises_for_zero_window_seconds(self) -> None:
        """Raise ValueError when RATE_LIMIT_ENABLED is true and window seconds is invalid."""
        with pytest.raises(
            ValueError,
            match="RATE_LIMIT_REQUESTS and RATE_LIMIT_WINDOW_SECONDS must be greater than 0",
        ):
            middleware_provider.MiddlewareProvider(Mock())._create_rate_limit_middleware()

    @pytest.mark.asyncio
    async def test_rate_limit_allows_below_threshold(self) -> None:
        """Allow request when below rate limit threshold."""
        app = AsyncMock()
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock()
        
        middleware = RateLimitMiddleware(app, cache, max_requests=10, window_seconds=60)
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="192.168.1.1")
        
        call_next = AsyncMock(return_value="response")
        result = await middleware.dispatch(request, call_next)
        
        assert result == "response"
        cache.set.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_rate_limit_rejects_at_threshold(self) -> None:
        """Reject request when rate limit threshold reached."""
        app = AsyncMock()
        cache = AsyncMock()
        cache.get = AsyncMock(return_value="10")  # Already at max
        cache.set = AsyncMock()
        
        middleware = RateLimitMiddleware(app, cache, max_requests=10, window_seconds=60)
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="192.168.1.1")
        
        call_next = AsyncMock()
        result = await middleware.dispatch(request, call_next)
        
        assert result.status_code == 429
        assert "Rate limit exceeded" in result.body.decode()
        call_next.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_rate_limit_includes_retry_after(self) -> None:
        """Include Retry-After header in rate limit response."""
        app = AsyncMock()
        cache = AsyncMock()
        cache.get = AsyncMock(return_value="10")
        
        middleware = RateLimitMiddleware(app, cache, max_requests=10, window_seconds=60)
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="192.168.1.1")
        
        call_next = AsyncMock()
        result = await middleware.dispatch(request, call_next)
        
        assert "Retry-After" in result.headers
        assert int(result.headers["Retry-After"]) >= 1

    @pytest.mark.asyncio
    async def test_rate_limit_increments_counter(self) -> None:
        """Increment counter on successful request."""
        app = AsyncMock()
        cache = AsyncMock()
        cache.get = AsyncMock(return_value="5")
        cache.set = AsyncMock()
        
        middleware = RateLimitMiddleware(app, cache, max_requests=10, window_seconds=60)
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="192.168.1.1")
        
        call_next = AsyncMock(return_value="response")
        result = await middleware.dispatch(request, call_next)
        
        # Should increment to 6
        cache.set.assert_awaited_once()
        call_args = cache.set.call_args
        assert call_args[0][1] == 6

    @pytest.mark.asyncio
    async def test_rate_limit_handles_invalid_cache_value(self) -> None:
        """Handle non-integer cache value gracefully."""
        app = AsyncMock()
        cache = AsyncMock()
        cache.get = AsyncMock(return_value="invalid")
        cache.set = AsyncMock()
        
        middleware = RateLimitMiddleware(app, cache, max_requests=10, window_seconds=60)
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="192.168.1.1")
        
        call_next = AsyncMock(return_value="response")
        result = await middleware.dispatch(request, call_next)
        
        # Should treat invalid value as 0
        assert result == "response"
        cache.set.assert_awaited_once()
        call_args = cache.set.call_args
        assert call_args[0][1] == 1

    @pytest.mark.asyncio
    async def test_rate_limit_uses_client_ip_as_key(self) -> None:
        """Use client IP as part of cache key."""
        app = AsyncMock()
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock()
        
        middleware = RateLimitMiddleware(app, cache, max_requests=10, window_seconds=60)
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="192.168.1.100")
        
        call_next = AsyncMock(return_value="response")
        await middleware.dispatch(request, call_next)
        
        # Check cache key includes IP
        call_args = cache.get.call_args[0]
        assert "192.168.1.100" in call_args[0]
        assert "RATELIMIT_" in call_args[0]