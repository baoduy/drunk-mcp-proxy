"""
Unit tests for src/auth_providers/auth_pass_through.py module.

Tests AuthPassThrough class for token pass-through authentication.
"""

from unittest.mock import Mock, patch, AsyncMock, MagicMock
import pytest
import httpx
from mcp.server.auth.provider import AccessToken

from src.auth_providers.auth_pass_through import AuthPassThrough


class TestAuthPassThroughGetToken:
    """Test suite for AuthPassThrough._get_token method."""

    @patch('src.auth_providers.auth_pass_through.get_access_token')
    def test_get_token_with_valid_token(self, mock_get_token):
        """Test _get_token returns token when available."""
        mock_token = Mock(spec=AccessToken)
        mock_token.token = "test-token-123"
        mock_get_token.return_value = mock_token

        auth = AuthPassThrough()
        result = auth._get_token()

        assert result == mock_token
        mock_get_token.assert_called_once()

    @patch('src.auth_providers.auth_pass_through.get_access_token')
    def test_get_token_with_no_token(self, mock_get_token):
        """Test _get_token returns None when token is not available."""
        mock_get_token.return_value = None

        auth = AuthPassThrough()
        result = auth._get_token()

        assert result is None
        mock_get_token.assert_called_once()

    @patch('src.auth_providers.auth_pass_through.logger')
    @patch('src.auth_providers.auth_pass_through.get_access_token')
    def test_get_token_logs_info_when_token_available(self, mock_get_token, mock_logger):
        """Test _get_token logs info message when token is available."""
        mock_token = Mock(spec=AccessToken)
        mock_token.token = "test-token-123"
        # Configure the mock to return a string representation that includes the token value
        mock_token.__str__ = Mock(return_value="test-token-123")
        mock_get_token.return_value = mock_token

        auth = AuthPassThrough()
        auth._get_token()

        mock_logger.info.assert_called_once()
        # Verify the logger was called with a message containing "Access token:"
        call_message = mock_logger.info.call_args[0][0]
        assert "Access token:" in call_message

    @patch('src.auth_providers.auth_pass_through.logger')
    @patch('src.auth_providers.auth_pass_through.get_access_token')
    def test_get_token_logs_warning_when_no_token(self, mock_get_token, mock_logger):
        """Test _get_token logs warning when token is not available."""
        mock_get_token.return_value = None

        auth = AuthPassThrough()
        auth._get_token()

        mock_logger.warning.assert_called_once()


class TestAuthPassThroughAuthFlow:
    """Test suite for AuthPassThrough.auth_flow method (sync)."""

    @patch('src.auth_providers.auth_pass_through.get_access_token')
    def test_auth_flow_adds_bearer_token(self, mock_get_token):
        """Test auth_flow adds Bearer token to request headers."""
        mock_token = Mock(spec=AccessToken)
        mock_token.token = "test-token-sync"
        mock_get_token.return_value = mock_token

        auth = AuthPassThrough()
        request = httpx.Request("GET", "https://api.example.com/test")

        # Collect all yielded requests from the generator
        gen = auth.auth_flow(request)
        modified_request = next(gen)

        assert "Authorization" in modified_request.headers
        assert modified_request.headers["Authorization"] == "Bearer test-token-sync"

    @patch('src.auth_providers.auth_pass_through.get_access_token')
    def test_auth_flow_without_token(self, mock_get_token):
        """Test auth_flow doesn't add Authorization header when no token."""
        mock_get_token.return_value = None

        auth = AuthPassThrough()
        request = httpx.Request("GET", "https://api.example.com/test")

        gen = auth.auth_flow(request)
        modified_request = next(gen)

        assert "Authorization" not in modified_request.headers

    @patch('src.auth_providers.auth_pass_through.get_access_token')
    def test_auth_flow_preserves_existing_headers(self, mock_get_token):
        """Test auth_flow preserves other request headers."""
        mock_token = Mock(spec=AccessToken)
        mock_token.token = "test-token"
        mock_get_token.return_value = mock_token

        auth = AuthPassThrough()
        request = httpx.Request(
            "GET",
            "https://api.example.com/test",
            headers={"X-Custom-Header": "custom-value"}
        )

        gen = auth.auth_flow(request)
        modified_request = next(gen)

        assert modified_request.headers["X-Custom-Header"] == "custom-value"
        assert modified_request.headers["Authorization"] == "Bearer test-token"

    @patch('src.auth_providers.auth_pass_through.get_access_token')
    def test_auth_flow_generator_yields_request(self, mock_get_token):
        """Test auth_flow is a generator that yields the request."""
        mock_token = Mock(spec=AccessToken)
        mock_token.token = "test-token"
        mock_get_token.return_value = mock_token

        auth = AuthPassThrough()
        request = httpx.Request("GET", "https://api.example.com/test")

        gen = auth.auth_flow(request)
        assert hasattr(gen, '__next__')  # Is a generator

        modified_request = next(gen)
        assert isinstance(modified_request, httpx.Request)


class TestAuthPassThroughAsyncAuthFlow:
    """Test suite for AuthPassThrough.async_auth_flow method (async)."""

    @pytest.mark.asyncio
    @patch('src.auth_providers.auth_pass_through.get_access_token')
    async def test_async_auth_flow_adds_bearer_token(self, mock_get_token):
        """Test async_auth_flow adds Bearer token to request headers."""
        mock_token = Mock(spec=AccessToken)
        mock_token.token = "test-token-async"
        mock_get_token.return_value = mock_token

        auth = AuthPassThrough()
        request = httpx.Request("GET", "https://api.example.com/test")

        # Collect from async generator
        async_gen = auth.async_auth_flow(request)
        modified_request = await async_gen.__anext__()

        assert "Authorization" in modified_request.headers
        assert modified_request.headers["Authorization"] == "Bearer test-token-async"

    @pytest.mark.asyncio
    @patch('src.auth_providers.auth_pass_through.get_access_token')
    async def test_async_auth_flow_without_token(self, mock_get_token):
        """Test async_auth_flow doesn't add header when no token."""
        mock_get_token.return_value = None

        auth = AuthPassThrough()
        request = httpx.Request("GET", "https://api.example.com/test")

        async_gen = auth.async_auth_flow(request)
        modified_request = await async_gen.__anext__()

        assert "Authorization" not in modified_request.headers

    @pytest.mark.asyncio
    @patch('src.auth_providers.auth_pass_through.get_access_token')
    async def test_async_auth_flow_preserves_headers(self, mock_get_token):
        """Test async_auth_flow preserves other headers."""
        mock_token = Mock(spec=AccessToken)
        mock_token.token = "test-token"
        mock_get_token.return_value = mock_token

        auth = AuthPassThrough()
        request = httpx.Request(
            "GET",
            "https://api.example.com/test",
            headers={"X-Custom-Header": "async-value", "Accept": "application/json"}
        )

        async_gen = auth.async_auth_flow(request)
        modified_request = await async_gen.__anext__()

        assert modified_request.headers["X-Custom-Header"] == "async-value"
        assert modified_request.headers["Accept"] == "application/json"
        assert modified_request.headers["Authorization"] == "Bearer test-token"

    @pytest.mark.asyncio
    @patch('src.auth_providers.auth_pass_through.get_access_token')
    async def test_async_auth_flow_is_async_generator(self, mock_get_token):
        """Test async_auth_flow is an async generator."""
        mock_token = Mock(spec=AccessToken)
        mock_token.token = "test-token"
        mock_get_token.return_value = mock_token

        auth = AuthPassThrough()
        request = httpx.Request("GET", "https://api.example.com/test")

        async_gen = auth.async_auth_flow(request)
        assert hasattr(async_gen, '__anext__')  # Is an async generator

        modified_request = await async_gen.__anext__()
        assert isinstance(modified_request, httpx.Request)


class TestAuthPassThroughEdgeCases:
    """Test suite for edge cases and error conditions."""

    @patch('src.auth_providers.auth_pass_through.get_access_token')
    def test_auth_flow_with_empty_token_string(self, mock_get_token):
        """Test auth_flow with empty token string (falsy value)."""
        mock_token = Mock(spec=AccessToken)
        mock_token.token = ""  # Empty token
        mock_get_token.return_value = mock_token

        auth = AuthPassThrough()
        request = httpx.Request("GET", "https://api.example.com/test")

        gen = auth.auth_flow(request)
        modified_request = next(gen)

        # Empty token should still add header
        assert "Authorization" in modified_request.headers
        assert modified_request.headers["Authorization"] == "Bearer "

    @patch('src.auth_providers.auth_pass_through.get_access_token')
    def test_auth_flow_with_special_characters_in_token(self, mock_get_token):
        """Test auth_flow correctly handles tokens with special characters."""
        special_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ0ZXN0In0.test=="
        mock_token = Mock(spec=AccessToken)
        mock_token.token = special_token
        mock_get_token.return_value = mock_token

        auth = AuthPassThrough()
        request = httpx.Request("GET", "https://api.example.com/test")

        gen = auth.auth_flow(request)
        modified_request = next(gen)

        assert modified_request.headers["Authorization"] == f"Bearer {special_token}"

    @patch('src.auth_providers.auth_pass_through.get_access_token')
    def test_auth_flow_with_post_request(self, mock_get_token):
        """Test auth_flow works with POST requests."""
        mock_token = Mock(spec=AccessToken)
        mock_token.token = "test-token"
        mock_get_token.return_value = mock_token

        auth = AuthPassThrough()
        request = httpx.Request(
            "POST",
            "https://api.example.com/endpoint",
            json={"key": "value"}
        )

        gen = auth.auth_flow(request)
        modified_request = next(gen)

        assert modified_request.headers["Authorization"] == "Bearer test-token"
        assert modified_request.method == "POST"

    @patch('src.auth_providers.auth_pass_through.get_access_token')
    def test_auth_flow_multiple_iterations(self, mock_get_token):
        """Test auth_flow can be called multiple times."""
        mock_token = Mock(spec=AccessToken)
        mock_token.token = "test-token-1"
        mock_get_token.return_value = mock_token

        auth = AuthPassThrough()

        # First request
        request1 = httpx.Request("GET", "https://api.example.com/test1")
        gen1 = auth.auth_flow(request1)
        modified_request1 = next(gen1)
        assert modified_request1.headers["Authorization"] == "Bearer test-token-1"

        # Second request with different token
        mock_get_token.return_value = Mock(spec=AccessToken, token="test-token-2")
        request2 = httpx.Request("GET", "https://api.example.com/test2")
        gen2 = auth.auth_flow(request2)
        modified_request2 = next(gen2)
        assert modified_request2.headers["Authorization"] == "Bearer test-token-2"


class TestAuthPassThroughHTTPXIntegration:
    """Test suite for httpx.Auth interface compliance."""

    def test_auth_pass_through_is_httpx_auth(self):
        """Test AuthPassThrough is a subclass of httpx.Auth."""
        assert issubclass(AuthPassThrough, httpx.Auth)

    @patch('src.auth_providers.auth_pass_through.get_access_token')
    def test_auth_can_be_used_with_httpx_client(self, mock_get_token):
        """Test AuthPassThrough can be passed to httpx.Client."""
        mock_token = Mock(spec=AccessToken)
        mock_token.token = "test-token"
        mock_get_token.return_value = mock_token

        auth = AuthPassThrough()
        
        # This should not raise an error
        # (actual HTTP call would require mocking)
        assert isinstance(auth, httpx.Auth)
        assert hasattr(auth, 'auth_flow')
        assert hasattr(auth, 'async_auth_flow')
