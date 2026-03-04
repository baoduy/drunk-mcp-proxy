import hashlib
from fastmcp.server.auth.auth import AccessToken, TokenVerifier
from pydantic.v1 import AnyHttpUrl
from drunk_ai_proxy.tools.logging_config import setup_logging


class ApiKeyAuthProvider(TokenVerifier):
    """Authentication provider that uses a static API key for authentication."""

    def __init__(self, token: str, base_url: AnyHttpUrl | str | None = None):
        super().__init__(
            base_url=base_url,
            required_scopes=None,
        )
        self.logger = setup_logging(__name__)
        self.token = token

    def _hash_token(self, token: str) -> str:
        """Hash a token to generate a client_id.

        Args:
            token: The raw token to hash

        Returns:
            SHA256 hash of the token as a hexadecimal string
        """
        return hashlib.sha256(token.encode()).hexdigest()

    async def verify_token(self, token: str) -> AccessToken | None:
        """Verify a bearer token and return access info if valid.

        All auth providers must implement token verification.

        Args:
            token: The token string to validate

        Returns:
            AccessToken object if valid, None if invalid or expired
        """
        if token == self.token:
            client_id = self._hash_token(token)
            self.logger.info(
                "Token verification successful (client_id: %s)", client_id[-4:]
            )
            return AccessToken(
                token=token,
                client_id=client_id,
                scopes=["*"],
                claims={"sub": client_id},
            )

        self.logger.info("Token verification failed: %s", token[-4:])
        return None
