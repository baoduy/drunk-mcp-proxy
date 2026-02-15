import asyncio
import time

import httpx


class OauthAsyncClient:
    def __init__(
            self,
            client_id: str,
            client_secret: str,
            token_url: str,
            scope: str | None = None,
            *,
            base_url: str,
            timeout: float = 30.0,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url
        self.scope = scope

        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
        )

        self._token: dict | None = None
        self._lock = asyncio.Lock()

    # =========================
    # PROPERTIES
    # =========================

    @property
    def base_url(self):
        """Return the base URL from the internal HTTP client."""
        return self._client.base_url

    @property
    def headers(self):
        """Return the headers from the internal HTTP client."""
        return self._client.headers

    @property
    def timeout(self):
        """Return the timeout from the internal HTTP client."""
        return self._client.timeout

    @property
    def is_closed(self) -> bool:
        """Return the is_closed status from the internal HTTP client."""
        return self._client.is_closed

    @property
    def params(self):
        """Return the params from the internal HTTP client."""
        return self._client.params

    # =========================
    # TOKEN MANAGEMENT
    # =========================

    async def _get_token(self):
        async with self._lock:
            if self._token and not self._is_token_expired():
                return self._token

            response = await self._client.post(
                self.token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": self.scope,
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded"
                },

            )

            response.raise_for_status()
            token = response.json()
            token["expires_at"] = (
                    time.time() + token.get("expires_in", 3600) - 60
            )

            self._token = token
            return token

    def _is_token_expired(self):
        return self._token["expires_at"] < time.time()

    # =========================
    # REQUEST WRAPPER
    # =========================

    async def request(self, method: str, url: str, **kwargs):
        token = await self._get_token()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token['access_token']}"

        return await self._client.request(
            method,
            url,
            headers=headers,
            **kwargs,

        )

    async def send(self, request: httpx.Request, **kwargs) -> httpx.Response:
        """Send a prepared request with OAuth authentication."""
        token = await self._get_token()
        request.headers["Authorization"] = f"Bearer {token['access_token']}"
        return await self._client.send(request, **kwargs)

    def build_request(self, method: str, url: str, **kwargs) -> httpx.Request:
        """Build an HTTP request without sending it."""
        return self._client.build_request(method, url, **kwargs)

    # =========================
    # HTTP VERBS
    # =========================

    async def get(self, url, **kwargs):
        return await self.request("GET", url, **kwargs)

    async def post(self, url, **kwargs):
        return await self.request("POST", url, **kwargs)

    async def put(self, url, **kwargs):
        return await self.request("PUT", url, **kwargs)

    async def delete(self, url, **kwargs):
        return await self.request("DELETE", url, **kwargs)

    async def patch(self, url, **kwargs):
        return await self.request("PATCH", url, **kwargs)

    # =========================
    # CLEANUP
    # =========================

    async def aclose(self):
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.aclose()
