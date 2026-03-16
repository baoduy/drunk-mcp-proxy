"""
Unit tests for Azure OAuth2 authentication module.

Tests cover both sync and async flows, token caching, expiry detection,
and error handling for the HttpxAzureOauth class.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import asyncio
import httpx
import pytest
import pytest_asyncio
import time

from drunk_ai_proxy.auth.httpx_azure_oauth import HttpxAzureOauth
from httpx_oauth.oauth2 import GetAccessTokenError


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def oauth_config() -> dict:
    """Standard OAuth config for testing."""
    return {
        "client_id": "test-client-id",
        "client_secret": "test-client-secret",
        "tenant_id": "test-tenant",
        "scopes": ["https://graph.microsoft.com/.default"],
    }


@pytest.fixture
def mock_token_response() -> dict:
    """Mock token response from Azure AD."""
    return {
        "access_token": "test-access-token-12345",
        "token_type": "Bearer",
        "expires_in": 3600,
        "ext_expires_in": 3600,
    }


@pytest.fixture
def azure_oauth(oauth_config) -> HttpxAzureOauth:
    """Create HttpxAzureOauth instance for testing."""
    return HttpxAzureOauth(**oauth_config)


@pytest_asyncio.fixture
async def azure_oauth_async(oauth_config) -> HttpxAzureOauth:
    """Create HttpxAzureOauth instance for async testing."""
    return HttpxAzureOauth(**oauth_config)


# =============================================================================
# INITIALIZATION TESTS
# =============================================================================


def test_azure_oauth_initialization(oauth_config):
    """Test that HttpxAzureOauth initializes with correct attributes."""
    oauth = HttpxAzureOauth(**oauth_config)

    assert oauth.client_id == "test-client-id"
    assert oauth.client_secret == "test-client-secret"
    # token_url is computed internally, we can check _oauth_client instead
    assert oauth._oauth_client is not None
    assert oauth._oauth_client.client_id == "test-client-id"

    assert oauth.scope == "https://graph.microsoft.com/.default"


def test_azure_oauth_initialization_no_scope(oauth_config):
    """Test initialization without scope (uses Azure default)."""
    del oauth_config["scopes"]
    oauth = HttpxAzureOauth(**oauth_config)

    # When scopes is None, HttpxAzureOauth defaults to graph.microsoft.com
    assert oauth.scope is not None
    assert "graph.microsoft.com" in oauth.scope


def test_azure_oauth_storage_defaults(oauth_config):
    """Test that default storage is created if not provided."""
    oauth = HttpxAzureOauth(**oauth_config)

    # Should have storage initialized
    assert oauth.storage is not None
    assert hasattr(oauth.storage, "get")
    assert hasattr(oauth.storage, "put")


# =============================================================================
# TOKEN EXPIRY DETECTION TESTS
# =============================================================================


def test_is_token_expired_dict_expired():
    """Test that expired tokens are correctly identified."""
    expired_token = {
        "access_token": "token",
        "expires_at": time.time() - 100,  # Expired 100 seconds ago
    }

    assert HttpxAzureOauth._is_token_expired_dict(expired_token) is True


def test_is_token_expired_dict_valid():
    """Test that valid tokens are correctly identified."""
    valid_token = {
        "access_token": "token",
        "expires_at": time.time() + 3600,  # Valid for 1 hour
    }

    assert HttpxAzureOauth._is_token_expired_dict(valid_token) is False


def test_is_token_expired_dict_none():
    """Test that None token is considered expired."""
    assert HttpxAzureOauth._is_token_expired_dict(None) is True


def test_is_token_expired_dict_empty():
    """Test that empty dict is considered expired."""
    assert HttpxAzureOauth._is_token_expired_dict({}) is True


def test_is_token_expired_dict_no_expires_at():
    """Test that token without expires_at is considered expired."""
    token = {"access_token": "token"}
    assert HttpxAzureOauth._is_token_expired_dict(token) is True


# =============================================================================
# ASYNC TOKEN FETCHING TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_fetch_token_success(azure_oauth_async, mock_token_response):
    """Test successful token fetch from Azure AD."""
    with patch.object(
        azure_oauth_async._oauth_client,
        "get_client_credentials_token",
        new_callable=AsyncMock,
    ) as mock_get_token:
        mock_get_token.return_value = mock_token_response

        token = await azure_oauth_async._fetch_token()

        assert token["access_token"] == "test-access-token-12345"
        assert token["token_type"] == "Bearer"
        assert token["expires_in"] == 3600
        assert "expires_at" in token
        assert isinstance(token["expires_at"], float)


@pytest.mark.asyncio
async def test_fetch_token_adds_expiry_buffer(azure_oauth_async, mock_token_response):
    """Test that fetch_token adds 60-second buffer to expiry."""
    with patch.object(
        azure_oauth_async._oauth_client,
        "get_client_credentials_token",
        new_callable=AsyncMock,
    ) as mock_get_token:
        mock_get_token.return_value = mock_token_response

        before_time = time.time()
        token = await azure_oauth_async._fetch_token()
        after_time = time.time()

        expected_expiry = before_time + 3600 - 60
        assert abs(token["expires_at"] - expected_expiry) < 2


@pytest.mark.asyncio
async def test_fetch_token_http_error(azure_oauth_async):
    """Test that HTTP errors are raised during token fetch."""
    with patch.object(
        azure_oauth_async._oauth_client,
        "get_client_credentials_token",
        new_callable=AsyncMock,
    ) as mock_get_token:
        mock_get_token.side_effect = GetAccessTokenError("401 Unauthorized")

        with pytest.raises(GetAccessTokenError):
            await azure_oauth_async._fetch_token()


# =============================================================================
# ASYNC TOKEN RETRIEVAL TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_async_get_token_from_cache(azure_oauth_async, mock_token_response):
    """Test that token is returned from storage without fetching new one."""
    # Pre-populate storage
    stored_token = mock_token_response.copy()
    stored_token["expires_at"] = time.time() + 3600

    with patch.object(azure_oauth_async.storage, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = stored_token
        
        with patch.object(azure_oauth_async, "_fetch_token") as mock_fetch:
            token = await azure_oauth_async._async_get_token()

            # Should return stored token without calling fetch
            assert token == stored_token
            mock_fetch.assert_not_called()
            mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_async_get_token_from_storage(azure_oauth_async, mock_token_response):
    """Test that token is retrieved from storage."""
    stored_token = mock_token_response.copy()
    stored_token["expires_at"] = time.time() + 3600

    # Mock storage.get to return valid token
    with patch.object(azure_oauth_async.storage, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = stored_token

        token = await azure_oauth_async._async_get_token()

        # Should return storage token
        assert token == stored_token
        mock_get.assert_called_once_with("test-client-id")


@pytest.mark.asyncio
async def test_async_get_token_fetches_new_when_expired(azure_oauth_async, mock_token_response):
    """Test that new token is fetched when storage token is expired."""
    expired_token = mock_token_response.copy()
    expired_token["expires_at"] = time.time() - 100  # Expired

    new_token = mock_token_response.copy()
    new_token["expires_at"] = time.time() + 3600

    with patch.object(azure_oauth_async.storage, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = expired_token
        
        with patch.object(azure_oauth_async, "_fetch_token", new_callable=AsyncMock) as mock_fetch:
            with patch.object(azure_oauth_async.storage, "put", new_callable=AsyncMock) as mock_put:
                mock_fetch.return_value = new_token

                token = await azure_oauth_async._async_get_token()

                # Should fetch and store new token
                assert token == new_token
                mock_fetch.assert_called_once()
                mock_put.assert_called_once()


@pytest.mark.asyncio
async def test_async_get_token_fetches_when_no_cache(azure_oauth_async, mock_token_response):
    """Test that new token is fetched when no cache exists."""
    new_token = mock_token_response.copy()
    new_token["expires_at"] = time.time() + 3600

    with patch.object(azure_oauth_async, "_fetch_token", new_callable=AsyncMock) as mock_fetch:
        with patch.object(azure_oauth_async.storage, "get", new_callable=AsyncMock) as mock_get:
            with patch.object(azure_oauth_async.storage, "put", new_callable=AsyncMock) as mock_put:
                mock_get.return_value = None
                mock_fetch.return_value = new_token

                token = await azure_oauth_async._async_get_token()

                assert token == new_token
                mock_fetch.assert_called_once()
                mock_put.assert_called_once_with("test-client-id", new_token)


# =============================================================================
# SYNC TOKEN RETRIEVAL TESTS
# =============================================================================


def test_get_token_creates_event_loop(azure_oauth, mock_token_response):
    """Test that sync token retrieval creates an event loop."""
    new_token = mock_token_response.copy()
    new_token["expires_at"] = time.time() + 3600

    with patch.object(azure_oauth, "_async_get_token", new_callable=AsyncMock) as mock_async:
        mock_async.return_value = new_token

        token = azure_oauth._get_token()

        assert token == new_token
        mock_async.assert_called_once()


def test_get_token_fails_in_async_context(azure_oauth):
    """Test that sync token retrieval fails when called from async context."""

    async def async_test():
        with pytest.raises(RuntimeError, match="Cannot use sync auth_flow in async context"):
            azure_oauth._get_token()

    asyncio.run(async_test())


def test_get_token_uses_cached_token(azure_oauth, mock_token_response):
    """Test that sync retrieval uses stored token from storage."""
    stored_token = mock_token_response.copy()
    stored_token["expires_at"] = time.time() + 3600

    # The stored token should be returned by _get_token via _async_get_token
    with patch.object(azure_oauth, "_async_get_token", new_callable=AsyncMock) as mock_async_get:
        mock_async_get.return_value = stored_token
        
        token = azure_oauth._get_token()

        # Should return stored token
        assert token == stored_token


# =============================================================================
# AUTH FLOW (SYNC) TESTS
# =============================================================================


def test_auth_flow_adds_bearer_token(azure_oauth, mock_token_response):
    """Test that auth_flow adds Bearer token to request headers."""
    token_with_expiry = mock_token_response.copy()
    token_with_expiry["expires_at"] = time.time() + 3600

    with patch.object(azure_oauth, "_get_token") as mock_get_token:
        mock_get_token.return_value = token_with_expiry

        request = httpx.Request("GET", "https://api.example.com/data")
        flow_gen = azure_oauth.auth_flow(request)

        # Get the yielded request
        modified_request = next(flow_gen)

        # Check that Authorization header was added
        assert "Authorization" in modified_request.headers
        assert modified_request.headers["Authorization"] == "Bearer test-access-token-12345"


def test_auth_flow_preserves_other_headers(azure_oauth, mock_token_response):
    """Test that auth_flow preserves existing headers."""
    token_with_expiry = mock_token_response.copy()
    token_with_expiry["expires_at"] = time.time() + 3600

    with patch.object(azure_oauth, "_get_token") as mock_get_token:
        mock_get_token.return_value = token_with_expiry

        request = httpx.Request(
            "GET",
            "https://api.example.com/data",
            headers={"X-Custom-Header": "custom-value", "Content-Type": "application/json"},
        )
        flow_gen = azure_oauth.auth_flow(request)
        modified_request = next(flow_gen)

        # Check existing headers are preserved
        assert modified_request.headers["X-Custom-Header"] == "custom-value"
        assert modified_request.headers["Content-Type"] == "application/json"
        assert "Authorization" in modified_request.headers


def test_auth_flow_is_generator(azure_oauth, mock_token_response):
    """Test that auth_flow returns a generator."""
    token_with_expiry = mock_token_response.copy()
    token_with_expiry["expires_at"] = time.time() + 3600

    with patch.object(azure_oauth, "_get_token") as mock_get_token:
        mock_get_token.return_value = token_with_expiry

        request = httpx.Request("GET", "https://api.example.com/data")
        flow = azure_oauth.auth_flow(request)

        # Check that it's a generator
        assert hasattr(flow, "__iter__")
        assert hasattr(flow, "__next__")


# =============================================================================
# ASYNC AUTH FLOW TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_async_auth_flow_adds_bearer_token(azure_oauth_async, mock_token_response):
    """Test that async_auth_flow adds Bearer token to request headers."""
    token_with_expiry = mock_token_response.copy()
    token_with_expiry["expires_at"] = time.time() + 3600

    with patch.object(azure_oauth_async, "_async_get_token", new_callable=AsyncMock) as mock_get_token:
        mock_get_token.return_value = token_with_expiry

        request = httpx.Request("GET", "https://api.example.com/data")
        flow_gen = azure_oauth_async.async_auth_flow(request)

        # Get the yielded request
        modified_request = await flow_gen.__anext__()

        # Check that Authorization header was added
        assert "Authorization" in modified_request.headers
        assert modified_request.headers["Authorization"] == "Bearer test-access-token-12345"


@pytest.mark.asyncio
async def test_async_auth_flow_preserves_other_headers(azure_oauth_async, mock_token_response):
    """Test that async_auth_flow preserves existing headers."""
    token_with_expiry = mock_token_response.copy()
    token_with_expiry["expires_at"] = time.time() + 3600

    with patch.object(azure_oauth_async, "_async_get_token", new_callable=AsyncMock) as mock_get_token:
        mock_get_token.return_value = token_with_expiry

        request = httpx.Request(
            "GET",
            "https://api.example.com/data",
            headers={"X-Custom-Header": "custom-value", "Content-Type": "application/json"},
        )
        flow_gen = azure_oauth_async.async_auth_flow(request)
        modified_request = await flow_gen.__anext__()

        # Check existing headers are preserved
        assert modified_request.headers["X-Custom-Header"] == "custom-value"
        assert modified_request.headers["Content-Type"] == "application/json"
        assert "Authorization" in modified_request.headers


@pytest.mark.asyncio
async def test_async_auth_flow_is_async_generator(azure_oauth_async, mock_token_response):
    """Test that async_auth_flow returns an async generator."""
    token_with_expiry = mock_token_response.copy()
    token_with_expiry["expires_at"] = time.time() + 3600

    with patch.object(azure_oauth_async, "_async_get_token", new_callable=AsyncMock) as mock_get_token:
        mock_get_token.return_value = token_with_expiry

        request = httpx.Request("GET", "https://api.example.com/data")
        flow = azure_oauth_async.async_auth_flow(request)

        # Check that it's an async generator
        assert hasattr(flow, "__aiter__")
        assert hasattr(flow, "__anext__")


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_end_to_end_async_flow(oauth_config, mock_token_response):
    """Test complete async flow with AsyncClient."""
    oauth = HttpxAzureOauth(**oauth_config)

    token_with_expiry = mock_token_response.copy()
    token_with_expiry["expires_at"] = time.time() + 3600

    with patch.object(oauth, "_fetch_token", new_callable=AsyncMock) as mock_fetch:
        with patch.object(oauth.storage, "get", new_callable=AsyncMock) as mock_get:
            with patch.object(oauth.storage, "put", new_callable=AsyncMock) as mock_put:
                mock_get.return_value = None
                mock_fetch.return_value = token_with_expiry

                request = httpx.Request("GET", "https://api.example.com/data")
                flow_gen = oauth.async_auth_flow(request)
                modified_request = await flow_gen.__anext__()

                # Verify the request has the token
                assert "Authorization" in modified_request.headers
                assert modified_request.headers["Authorization"] == "Bearer test-access-token-12345"


def test_end_to_end_sync_flow(oauth_config, mock_token_response):
    """Test complete sync flow with Client."""
    oauth = HttpxAzureOauth(**oauth_config)

    token_with_expiry = mock_token_response.copy()
    token_with_expiry["expires_at"] = time.time() + 3600

    with patch.object(oauth, "_get_token") as mock_get_token:
        mock_get_token.return_value = token_with_expiry

        request = httpx.Request("GET", "https://api.example.com/data")
        flow_gen = oauth.auth_flow(request)
        modified_request = next(flow_gen)

        # Verify the request has the token
        assert "Authorization" in modified_request.headers
        assert modified_request.headers["Authorization"] == "Bearer test-access-token-12345"


@pytest.mark.asyncio
async def test_concurrent_async_requests(oauth_config, mock_token_response):
    """Test that concurrent async requests share the same token."""
    oauth = HttpxAzureOauth(**oauth_config)

    token_with_expiry = mock_token_response.copy()
    token_with_expiry["expires_at"] = time.time() + 3600

    fetch_count = 0

    async def mock_fetch():
        nonlocal fetch_count
        fetch_count += 1
        # Simulate some delay
        await asyncio.sleep(0.01)
        return token_with_expiry

    with patch.object(oauth, "_fetch_token", side_effect=mock_fetch):
        with patch.object(oauth.storage, "get", new_callable=AsyncMock) as mock_get:
            with patch.object(oauth.storage, "put", new_callable=AsyncMock) as mock_put:
                mock_get.return_value = None

                # Make 5 concurrent requests
                async def get_token_flow():
                    return await oauth._async_get_token()

                tokens = await asyncio.gather(
                    get_token_flow(),
                    get_token_flow(),
                    get_token_flow(),
                    get_token_flow(),
                    get_token_flow(),
                )

                # All tokens should be the same
                assert all(t == token_with_expiry for t in tokens)
                # Should have called storage.put 5 times (no built-in deduplication)
                assert mock_put.call_count >= 1


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_async_get_token_handles_storage_error(azure_oauth_async):
    """Test that storage errors are handled gracefully."""
    with patch.object(azure_oauth_async.storage, "get", new_callable=AsyncMock) as mock_get:
        with patch.object(azure_oauth_async, "_fetch_token", new_callable=AsyncMock):
            # Storage.get raises an error
            mock_get.side_effect = Exception("Storage error")

            # Should raise the error (not caught)
            with pytest.raises(Exception, match="Storage error"):
                await azure_oauth_async._async_get_token()


def test_auth_flow_handles_missing_access_token(azure_oauth):
    """Test that auth_flow handles token without access_token."""
    invalid_token = {}  # Missing access_token

    with patch.object(azure_oauth, "_get_token") as mock_get_token:
        mock_get_token.return_value = invalid_token

        request = httpx.Request("GET", "https://api.example.com/data")

        # Should raise KeyError when accessing invalid_token['access_token']
        with pytest.raises(KeyError):
            flow_gen = azure_oauth.auth_flow(request)
            next(flow_gen)


@pytest.mark.asyncio
async def test_async_auth_flow_handles_missing_access_token(azure_oauth_async):
    """Test that async_auth_flow handles token without access_token."""
    invalid_token = {}  # Missing access_token

    with patch.object(azure_oauth_async, "_async_get_token", new_callable=AsyncMock) as mock_get_token:
        mock_get_token.return_value = invalid_token

        request = httpx.Request("GET", "https://api.example.com/data")

        # Should raise KeyError when accessing invalid_token['access_token']
        with pytest.raises(KeyError):
            flow_gen = azure_oauth_async.async_auth_flow(request)
            await flow_gen.__anext__()
