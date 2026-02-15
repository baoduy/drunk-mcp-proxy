"""Comprehensive tests for OauthAsyncClient class."""

import time

import httpx

from src.tools.oauth_client import OauthAsyncClient


class TestOauthAsyncClientInitialization:
    """Tests for OauthAsyncClient initialization."""

    def test_init_with_required_params(self):
        """Test initialization with required parameters."""
        client = OauthAsyncClient(
            client_id="test-id",
            client_secret="test-secret",
            token_url="https://example.com/token",
            base_url="https://api.example.com",
        )

        assert client.client_id == "test-id"
        assert client.client_secret == "test-secret"
        assert client.token_url == "https://example.com/token"
        assert client.scope is None
        assert client._token is None

    def test_init_with_scope(self):
        """Test initialization with scope parameter."""
        client = OauthAsyncClient(
            client_id="test-id",
            client_secret="test-secret",
            token_url="https://example.com/token",
            scope="read write",
            base_url="https://api.example.com",
        )

        assert client.scope == "read write"

    def test_init_with_timeout(self):
        """Test initialization with custom timeout."""
        client = OauthAsyncClient(
            client_id="test-id",
            client_secret="test-secret",
            token_url="https://example.com/token",
            base_url="https://api.example.com",
            timeout=60.0,
        )

        # Timeout is an httpx.Timeout object, check it exists and has reasonable value
        assert client.timeout is not None
        assert client._client.timeout is not None


class TestOauthAsyncClientProperties:
    """Tests for OauthAsyncClient properties."""

    def test_base_url_property(self):
        """Test base_url property returns correct URL."""
        client = OauthAsyncClient(
            client_id="test-id",
            client_secret="test-secret",
            token_url="https://example.com/token",
            base_url="https://api.example.com",
        )

        assert "https://api.example.com" in str(client.base_url)

    def test_headers_property(self):
        """Test headers property returns httpx.Headers."""
        client = OauthAsyncClient(
            client_id="test-id",
            client_secret="test-secret",
            token_url="https://example.com/token",
            base_url="https://api.example.com",
        )

        assert isinstance(client.headers, httpx.Headers)
        assert "user-agent" in client.headers

    def test_timeout_property(self):
        """Test timeout property returns timeout configuration."""
        client = OauthAsyncClient(
            client_id="test-id",
            client_secret="test-secret",
            token_url="https://example.com/token",
            base_url="https://api.example.com",
            timeout=45.0,
        )

        assert client.timeout is not None
        assert client._client.timeout is not None

    def test_is_closed_property_initial(self):
        """Test is_closed property is False when just created."""
        client = OauthAsyncClient(
            client_id="test-id",
            client_secret="test-secret",
            token_url="https://example.com/token",
            base_url="https://api.example.com",
        )

        assert client.is_closed is False

    def test_params_property(self):
        """Test params property returns QueryParams."""
        client = OauthAsyncClient(
            client_id="test-id",
            client_secret="test-secret",
            token_url="https://example.com/token",
            base_url="https://api.example.com",
        )

        assert isinstance(client.params, httpx.QueryParams)


class TestOauthAsyncClientBuildRequest:
    """Tests for build_request method."""

    def test_build_request_get(self):
        """Test building a GET request."""
        client = OauthAsyncClient(
            client_id="test-id",
            client_secret="test-secret",
            token_url="https://example.com/token",
            base_url="https://api.example.com",
        )

        request = client.build_request("GET", "/api/resource")

        assert isinstance(request, httpx.Request)
        assert request.method == "GET"
        assert "/api/resource" in str(request.url)

    def test_build_request_post_with_json(self):
        """Test building a POST request with JSON data."""
        client = OauthAsyncClient(
            client_id="test-id",
            client_secret="test-secret",
            token_url="https://example.com/token",
            base_url="https://api.example.com",
        )

        request = client.build_request("POST", "/api/resource", json={"key": "value"})

        assert isinstance(request, httpx.Request)
        assert request.method == "POST"
        assert request.content == b'{"key":"value"}'

    def test_build_request_with_headers(self):
        """Test building a request with custom headers."""
        client = OauthAsyncClient(
            client_id="test-id",
            client_secret="test-secret",
            token_url="https://example.com/token",
            base_url="https://api.example.com",
        )

        custom_headers = {"X-Custom": "value"}
        request = client.build_request("GET", "/api/resource", headers=custom_headers)

        assert request.headers["X-Custom"] == "value"


class TestOauthAsyncClientTokenManagement:
    """Tests for token management methods."""

    def test_is_token_expired_with_expired_token(self):
        """Test _is_token_expired returns True for expired token."""
        client = OauthAsyncClient(
            client_id="test-id",
            client_secret="test-secret",
            token_url="https://example.com/token",
            base_url="https://api.example.com",
        )

        # Set token with expired timestamp
        client._token = {
            "access_token": "test-token",
            "expires_at": time.time() - 100  # Expired 100 seconds ago
        }

        assert client._is_token_expired() is True

    def test_is_token_expired_with_valid_token(self):
        """Test _is_token_expired returns False for valid token."""
        client = OauthAsyncClient(
            client_id="test-id",
            client_secret="test-secret",
            token_url="https://example.com/token",
            base_url="https://api.example.com",
        )

        # Set token with future timestamp
        client._token = {
            "access_token": "test-token",
            "expires_at": time.time() + 3600  # Expires in 1 hour
        }

        assert client._is_token_expired() is False


class TestOauthAsyncClientLifecycle:
    """Tests for client lifecycle management."""

    def test_client_is_httpx_async_client_compatible(self):
        """Test that OauthAsyncClient is compatible with httpx.AsyncClient interface."""
        client = OauthAsyncClient(
            client_id="test-id",
            client_secret="test-secret",
            token_url="https://example.com/token",
            base_url="https://api.example.com",
        )

        # Check all required httpx.AsyncClient properties/methods exist
        assert hasattr(client, 'base_url')
        assert hasattr(client, 'headers')
        assert hasattr(client, 'timeout')
        assert hasattr(client, 'is_closed')
        assert hasattr(client, 'params')
        assert hasattr(client, 'request')
        assert hasattr(client, 'send')
        assert hasattr(client, 'build_request')
        assert hasattr(client, 'get')
        assert hasattr(client, 'post')
        assert hasattr(client, 'put')
        assert hasattr(client, 'delete')
        assert hasattr(client, 'patch')
        assert hasattr(client, 'aclose')
        assert hasattr(client, '__aenter__')
        assert hasattr(client, '__aexit__')

    def test_methods_are_callable(self):
        """Test that all required methods are callable."""
        client = OauthAsyncClient(
            client_id="test-id",
            client_secret="test-secret",
            token_url="https://example.com/token",
            base_url="https://api.example.com",
        )

        # Check all methods are callable
        assert callable(client.request)
        assert callable(client.send)
        assert callable(client.build_request)
        assert callable(client.get)
        assert callable(client.post)
        assert callable(client.put)
        assert callable(client.delete)
        assert callable(client.patch)
        assert callable(client.aclose)
        assert callable(client._get_token)
        assert callable(client._is_token_expired)

    def test_build_request_integration(self):
        """Test build_request works with all HTTP methods."""
        client = OauthAsyncClient(
            client_id="test-id",
            client_secret="test-secret",
            token_url="https://example.com/token",
            base_url="https://api.example.com",
        )

        methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]
        for method in methods:
            request = client.build_request(method, "/api/resource")
            assert request.method == method
            assert isinstance(request, httpx.Request)

    def test_send_method_signature(self):
        """Test send method accepts request and kwargs."""
        client = OauthAsyncClient(
            client_id="test-id",
            client_secret="test-secret",
            token_url="https://example.com/token",
            base_url="https://api.example.com",
        )

        # Test that send method exists and is properly defined
        import inspect
        sig = inspect.signature(client.send)
        assert 'request' in sig.parameters
        assert 'kwargs' in str(sig)

    def test_request_method_signature(self):
        """Test request method accepts method, url, and kwargs."""
        client = OauthAsyncClient(
            client_id="test-id",
            client_secret="test-secret",
            token_url="https://example.com/token",
            base_url="https://api.example.com",
        )

        # Test that request method exists and is properly defined
        import inspect
        sig = inspect.signature(client.request)
        assert 'method' in sig.parameters
        assert 'url' in sig.parameters
        assert 'kwargs' in str(sig)


class TestOauthAsyncClientIntegration:
    """Integration tests for OauthAsyncClient."""

    def test_internal_client_is_httpx_async_client(self):
        """Test that internal _client is an httpx.AsyncClient."""
        client = OauthAsyncClient(
            client_id="test-id",
            client_secret="test-secret",
            token_url="https://example.com/token",
            base_url="https://api.example.com",
        )

        assert isinstance(client._client, httpx.AsyncClient)
        assert client._client.base_url == client.base_url

    def test_client_has_asyncio_lock(self):
        """Test that client has asyncio lock for token management."""
        client = OauthAsyncClient(
            client_id="test-id",
            client_secret="test-secret",
            token_url="https://example.com/token",
            base_url="https://api.example.com",
        )

        assert hasattr(client, '_lock')
        import asyncio
        assert isinstance(client._lock, asyncio.Lock)

    def test_build_request_url_construction(self):
        """Test that build_request properly constructs URLs with base_url."""
        client = OauthAsyncClient(
            client_id="test-id",
            client_secret="test-secret",
            token_url="https://example.com/token",
            base_url="https://api.example.com",
        )

        request = client.build_request("GET", "/v1/users")
        assert "https://api.example.com" in str(request.url)
        assert "/v1/users" in str(request.url)

    def test_build_request_with_query_params(self):
        """Test build_request with query parameters."""
        client = OauthAsyncClient(
            client_id="test-id",
            client_secret="test-secret",
            token_url="https://example.com/token",
            base_url="https://api.example.com",
        )

        request = client.build_request("GET", "/api/items", params={"limit": 10, "offset": 0})
        assert "limit=10" in str(request.url)
        assert "offset=0" in str(request.url)
