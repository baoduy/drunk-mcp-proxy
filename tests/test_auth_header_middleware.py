"""
Unit tests for src/middleware/auth_header_middleware module.

Tests the AuthHeaderMiddleware for request path handling and token validation.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from drunk_ai_proxy.middleware.auth_header_middleware import AuthHeaderMiddleware
from drunk_ai_proxy.utils.auth_header_policy import DEFAULT_ANONYMOUS_PATHS


class TestAuthHeaderMiddlewareInit:
    """Test suite for AuthHeaderMiddleware initialization."""

    def test_init_default_anonymous_paths(self):
        """Test initialization with default anonymous paths."""
        middleware = AuthHeaderMiddleware()
        assert middleware.anonymous_paths == list(DEFAULT_ANONYMOUS_PATHS)

    def test_init_custom_anonymous_paths(self):
        """Test initialization with custom anonymous paths."""
        custom_paths = ["/status", "/metrics"]
        middleware = AuthHeaderMiddleware(anonymous_paths=custom_paths)
        assert middleware.anonymous_paths == custom_paths

    def test_init_empty_anonymous_paths(self):
        """Test initialization with empty anonymous paths list defaults to shared defaults."""
        middleware = AuthHeaderMiddleware(anonymous_paths=[])
        # Empty list is falsy, so defaults to shared defaults
        assert middleware.anonymous_paths == list(DEFAULT_ANONYMOUS_PATHS)

    def test_init_none_anonymous_paths(self):
        """Test initialization with None uses defaults."""
        middleware = AuthHeaderMiddleware(anonymous_paths=None)
        assert middleware.anonymous_paths == list(DEFAULT_ANONYMOUS_PATHS)


class TestGetRequestPath:
    """Test suite for _get_request_path method."""

    def test_get_request_path_from_context_path(self):
        """Test extracting path directly from context.path."""
        middleware = AuthHeaderMiddleware()
        context = Mock()
        context.path = "/api/users"

        result = middleware._get_request_path(context)
        assert result == "/api/users"

    def test_get_request_path_from_request_url(self):
        """Test extracting path from context.request.url.path."""
        middleware = AuthHeaderMiddleware()
        context = Mock()
        context.path = None
        context.request = Mock()
        context.request.url = Mock()
        context.request.url.path = "/api/health"

        result = middleware._get_request_path(context)
        assert result == "/api/health"

    def test_get_request_path_no_path_available(self):
        """Test when no path information is available."""
        middleware = AuthHeaderMiddleware()
        context = Mock(spec=[])  # Empty spec to prevent attribute access

        result = middleware._get_request_path(context)
        assert result is None

    def test_get_request_path_context_path_priority(self):
        """Test that context.path takes priority over request.url.path."""
        middleware = AuthHeaderMiddleware()
        context = Mock()
        context.path = "/direct/path"
        context.request = Mock()
        context.request.url = Mock()
        context.request.url.path = "/request/path"

        result = middleware._get_request_path(context)
        assert result == "/direct/path"

    def test_get_request_path_malformed_request(self):
        """Test with malformed request structure."""
        middleware = AuthHeaderMiddleware()
        context = Mock()
        context.path = None
        context.request = Mock()
        context.request.url = None

        result = middleware._get_request_path(context)
        assert result is None


class TestShouldValidateAuth:
    """Test suite for _should_validate_auth method."""

    def test_should_validate_auth_protected_path(self):
        """Test that protected paths require validation."""
        middleware = AuthHeaderMiddleware()
        assert middleware._should_validate_auth("/api/users") is True

    def test_should_validate_auth_anonymous_path_health(self):
        """Test that /health endpoint skips validation."""
        middleware = AuthHeaderMiddleware()
        assert middleware._should_validate_auth("/health") is False

    def test_should_validate_auth_anonymous_path_docs(self):
        """Test that /docs endpoint skips validation."""
        middleware = AuthHeaderMiddleware()
        assert middleware._should_validate_auth("/docs") is False

    def test_should_validate_auth_anonymous_path_root(self):
        """Test that / endpoint skips validation."""
        middleware = AuthHeaderMiddleware()
        assert middleware._should_validate_auth("/") is False

    def test_should_validate_auth_custom_anonymous_paths(self):
        """Test with custom anonymous paths."""
        middleware = AuthHeaderMiddleware(
            anonymous_paths=["/status", "/metrics"]
        )
        assert middleware._should_validate_auth("/status") is False
        assert middleware._should_validate_auth("/metrics") is False
        assert middleware._should_validate_auth("/api/users") is True

    def test_should_validate_auth_none_path(self):
        """Test with None path (should validate)."""
        middleware = AuthHeaderMiddleware()
        assert middleware._should_validate_auth(None) is True

    def test_should_validate_auth_empty_anonymous_list(self):
        """Test with empty anonymous paths list defaults to shared defaults."""
        # Empty list is falsy and defaults to shared defaults
        middleware = AuthHeaderMiddleware(anonymous_paths=[])
        assert middleware._should_validate_auth("/health") is False
        assert middleware._should_validate_auth("/docs") is False
        assert middleware._should_validate_auth("/") is False


class TestValidateAccessToken:
    """Test suite for _validate_access_token method."""

    @patch("drunk_ai_proxy.middleware.auth_header_middleware.logger")
    @patch("drunk_ai_proxy.middleware.auth_header_middleware.get_access_token")
    def test_validate_access_token_present(self, mock_get_token, mock_logger):
        """Test logging when access token is present."""
        mock_token = Mock()
        mock_token.client_id = "test-client"
        mock_get_token.return_value = mock_token

        middleware = AuthHeaderMiddleware()
        middleware._validate_access_token()

        mock_get_token.assert_called_once()
        mock_logger.info.assert_called_once()
        assert "Access token present" in mock_logger.info.call_args[0][0]

    @patch("drunk_ai_proxy.middleware.auth_header_middleware.logger")
    @patch("drunk_ai_proxy.middleware.auth_header_middleware.get_access_token")
    def test_validate_access_token_absent(self, mock_get_token, mock_logger):
        """Test logging when access token is not available."""
        mock_get_token.return_value = None

        middleware = AuthHeaderMiddleware()
        middleware._validate_access_token()

        mock_get_token.assert_called_once()
        mock_logger.warning.assert_called_once()


class TestOnMessage:
    """Test suite for on_message method."""

    @pytest.mark.asyncio
    @patch("drunk_ai_proxy.middleware.auth_header_middleware.get_access_token")
    async def test_on_message_request_type_with_protected_path(self, mock_get_token):
        """Test on_message validates token for protected paths."""
        mock_token = Mock()
        mock_token.client_id = "test-client"
        mock_get_token.return_value = mock_token

        middleware = AuthHeaderMiddleware()
        context = Mock()
        context.type = "request"
        context.path = "/api/users"

        call_next = AsyncMock()
        call_next.return_value = {"status": "ok"}

        result = await middleware.on_message(context, call_next)

        mock_get_token.assert_called_once()
        assert result == {"status": "ok"}
        call_next.assert_called_once_with(context)

    @pytest.mark.asyncio
    @patch("drunk_ai_proxy.middleware.auth_header_middleware.get_access_token")
    async def test_on_message_request_type_with_anonymous_path(self, mock_get_token):
        """Test on_message skips validation for anonymous paths."""
        middleware = AuthHeaderMiddleware()
        context = Mock()
        context.type = "request"
        context.path = "/health"

        call_next = AsyncMock()
        call_next.return_value = {"status": "ok"}

        result = await middleware.on_message(context, call_next)

        mock_get_token.assert_not_called()
        assert result == {"status": "ok"}
        call_next.assert_called_once_with(context)

    @pytest.mark.asyncio
    @patch("drunk_ai_proxy.middleware.auth_header_middleware.get_access_token")
    async def test_on_message_non_request_type(self, mock_get_token):
        """Test on_message ignores non-request types."""
        middleware = AuthHeaderMiddleware()
        context = Mock()
        context.type = "response"

        call_next = AsyncMock()
        call_next.return_value = {"status": "ok"}

        result = await middleware.on_message(context, call_next)

        mock_get_token.assert_not_called()
        assert result == {"status": "ok"}

    @pytest.mark.asyncio
    @patch("drunk_ai_proxy.middleware.auth_header_middleware.get_access_token")
    async def test_on_message_custom_anonymous_paths(self, mock_get_token):
        """Test on_message with custom anonymous paths."""
        middleware = AuthHeaderMiddleware(
            anonymous_paths=["/status", "/metrics"]
        )
        context = Mock()
        context.type = "request"
        context.path = "/metrics"

        call_next = AsyncMock()
        call_next.return_value = {"status": "ok"}

        result = await middleware.on_message(context, call_next)

        mock_get_token.assert_not_called()
        assert result == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_on_message_passes_context_to_call_next(self):
        """Test that on_message passes context to call_next."""
        middleware = AuthHeaderMiddleware(anonymous_paths=["/health"])
        context = Mock()
        context.type = "request"
        context.path = "/health"

        call_next = AsyncMock()
        call_next.return_value = "response"

        await middleware.on_message(context, call_next)

        call_next.assert_called_once_with(context)
