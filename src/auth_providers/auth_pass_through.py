import typing
import logging

import httpx
from fastmcp.server.dependencies import get_access_token
from mcp.server.auth.provider import AccessToken

logger = logging.getLogger(__name__)


class AuthPassThrough(httpx.Auth):
    """Authentication provider that passes through a static bearer token from calling client."""

    def _get_token(self) -> "AccessToken | None":
        token = get_access_token()
        if token:
            logger.info("Access token obtained")
        else:
            logger.warning("No access token available")
        return token

    def auth_flow(
        self, request: httpx.Request
    ) -> typing.Generator[httpx.Request, httpx.Response, None]:
        token = self._get_token()
        if token:
            request.headers["Authorization"] = f"Bearer {token.token}"
        yield request

    async def async_auth_flow(
        self, request: httpx.Request
    ) -> typing.AsyncGenerator[httpx.Request, httpx.Response]:
        token = self._get_token()
        if token:
            request.headers["Authorization"] = f"Bearer {token.token}"
        yield request