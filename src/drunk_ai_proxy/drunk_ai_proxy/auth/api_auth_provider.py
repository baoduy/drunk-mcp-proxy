import hashlib
from fastmcp.server.auth.auth import AccessToken, TokenVerifier
from pydantic import AnyUrl

from fastmcp.utilities import logging
logger = logging.get_logger(__name__)


class ApiKeyAuthProvider(TokenVerifier):
    """Authentication provider that uses a static API key for authentication."""

    def __init__(self, token: str, base_url: AnyUrl | str | None = None):
        super().__init__(
            base_url=base_url,
            required_scopes=None,
        )
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
            logger.info(
                "Token verification successful (client_id: %s)", client_id[-4:]
            )
            return AccessToken(
                token=token,
                client_id=client_id,
                scopes=["*"],
                claims={"sub": client_id},
            )

        logger.info("Token verification failed: %s", token[-4:])
        return None
