import pytest
import hashlib
from drunk_ai_proxy.auth_providers.api_auth_provider import ApiKeyAuthProvider
from fastmcp.server.auth.auth import AccessToken


class TestApiKeyAuthProvider:
    def test_hash_token_sha256(self):
        """Test that the implementation uses SHA256."""
        token = "test-token"
        provider = ApiKeyAuthProvider(token=token)

        # New implementation uses SHA256
        hashed = provider._hash_token(token)
        expected_sha256 = hashlib.sha256(token.encode()).hexdigest()

        assert hashed == expected_sha256
        assert len(hashed) == 64  # SHA256 length

    @pytest.mark.asyncio
    async def test_verify_token_success(self):
        token = "test-token"
        provider = ApiKeyAuthProvider(token=token)

        result = await provider.verify_token(token)

        assert isinstance(result, AccessToken)
        assert result.token == token
        assert result.client_id == hashlib.sha256(token.encode()).hexdigest()
        assert result.scopes == ["*"]

    @pytest.mark.asyncio
    async def test_verify_token_failure(self):
        token = "test-token"
        provider = ApiKeyAuthProvider(token=token)

        result = await provider.verify_token("wrong-token")

        assert result is None
