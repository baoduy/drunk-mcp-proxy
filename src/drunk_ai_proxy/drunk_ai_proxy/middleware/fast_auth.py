"""FastAPI auth dependency middleware for bearer-token validation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Request
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.security.http import HTTPBase
from fastapi.security.utils import get_authorization_scheme_param

if TYPE_CHECKING:
    from fastmcp.server.auth import AuthProvider


class FastAuthMiddleware(HTTPBase):
    """Validate and authorize bearer tokens using a FastMCP auth provider."""

    def __init__(self, auth_provider: "AuthProvider"):
        super().__init__(scheme="bearer")
        self.auth_provider = auth_provider
        self.auto_error = True

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials | None:
        authorization = request.headers.get("Authorization")
        scheme, token = get_authorization_scheme_param(authorization)

        if not (authorization and scheme and token):
            raise self.make_not_authenticated_error()

        rs = await self.auth_provider.verify_token(token)
        if rs is not None and (rs.claims.__len__() > 0 or rs.scopes.__len__() > 0):
            return HTTPAuthorizationCredentials(scheme=scheme, credentials=token)
        raise self.make_not_authenticated_error()
