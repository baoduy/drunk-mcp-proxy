"""Tests for OpenAPI provider OAuth client creation."""

from typing import Any, Optional

import httpx

from src.proxies.openapi_mcp_provider import OpenApiMcpProvider
from src.tools import SpecConfig


def _build_spec(name: str, auth: Optional[dict[str, Any]] = None,
                base_url: Optional[str] = "https://api.example.com") -> SpecConfig:
    payload: dict[str, Any] = {
        "name": name,
        "specFile": "dummy-openapi.json",
        "specType": "openapi",
        "auth": auth,
    }
    if base_url is not None:
        payload["baseUrl"] = base_url

    spec = SpecConfig.model_validate(payload)
    spec.spec_data = {"openapi": "3.0.1", "paths": {"/": {"get": {}}}}
    return spec


def test_create_client_without_auth_returns_async_client() -> None:
    provider = OpenApiMcpProvider(_build_spec("no-auth"))
    client = provider.create_client()

    assert isinstance(client, httpx.AsyncClient)


def _azure_auth_payload() -> dict[str, Any]:
    return {
        "azure": {
            "tokenUrl": "https://login.microsoftonline.com/tenant/oauth2/v2.0/token",
            "clientId": "client-id",
            "clientSecret": "client-secret",
            "tenantId": "tenant",
            "scopes": ["https://management.azure.com/.default"],
        }
    }


def test_create_client_with_azure_auth_with_base_url() -> None:
    """Test that OAuth client is created when Azure auth is configured with base_url."""
    from src.tools.oauth_client import OauthAsyncClient

    config = _build_spec("with-auth-base", auth=_azure_auth_payload(), base_url="https://api.example.com")
    provider = OpenApiMcpProvider(config)
    client = provider.create_client()

    # Should return OauthAsyncClient with base_url set
    assert isinstance(client, OauthAsyncClient)
    assert str(client.base_url) == "https://api.example.com/"
