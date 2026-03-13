"""On-demand remote resource fetch and cache service.

This module provides :class:`OnDemandRemoteResourceService`, a cache-aside
service that fetches remote HTTPS content on first access and stores it in
a TTL-backed cache store.  Subsequent requests within the TTL window are
served from cache without hitting the remote endpoint.

Security controls applied to every outbound request:

- HTTPS-only (SSRF prevention)
- ``follow_redirects=False``
- Extension/content-type allow-list
- Configurable maximum response size
- Optional ``ETag`` / ``If-None-Match`` conditional request support

Cache key format: ``remote_resource:{uri}``
"""

from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Mapping
from typing import TYPE_CHECKING, cast

import httpx

from drunk_ai_proxy.app.cache_provider import TTLAsyncKeyValue
from drunk_ai_proxy.utils.env import REMOTE_RESOURCE_TTL_HOURS

from fastmcp.utilities import logging

if TYPE_CHECKING:
    pass

logger = logging.get_logger(__name__)

# Allow-list of file extensions that remote resources may use.
_ALLOWED_EXTENSIONS: frozenset[str] = frozenset(
    {".md", ".yaml", ".yml", ".json", ".py", ".js", ".ts", ".txt"}
)

# Allow-list of content-type prefixes that remote resources may return.
_ALLOWED_CONTENT_TYPE_PREFIXES: tuple[str, ...] = (
    "text/",
    "application/json",
    "application/yaml",
    "application/x-yaml",
)

# Default maximum response size in bytes (10 MB)
_DEFAULT_MAX_SIZE_BYTES: int = 10 * 1024 * 1024

_CACHE_KEY_PREFIX = "remote_resource"


@dataclass
class RemoteResourceEntry:
    """Cached content metadata for a single remote resource."""

    content: str
    """Decoded text content of the remote resource."""

    content_type: str
    """MIME type reported by the remote server."""

    etag: str | None = field(default=None)
    """Optional ETag value for conditional re-validation."""

    last_modified: str | None = field(default=None)
    """Optional Last-Modified header value."""


class OnDemandRemoteResourceService:
    """Cache-aside service for on-demand remote HTTPS resource fetching.

    Fetches remote HTTPS content on first access and stores the result in a
    :class:`~drunk_ai_proxy.app.cache_provider.TTLAsyncKeyValue` store.
    Subsequent accesses within the TTL window are served from cache.

    The service enforces strict security controls on all outbound requests
    to reduce SSRF exposure.

    Args:
        cache: TTL-aware cache store instance.
        http_client: Shared ``httpx.AsyncClient`` used for outbound requests.
        max_size_bytes: Maximum permitted response body size in bytes.
    """

    def __init__(
        self,
        cache: TTLAsyncKeyValue,
        http_client: httpx.AsyncClient,
        max_size_bytes: int = _DEFAULT_MAX_SIZE_BYTES,
    ) -> None:
        """Initialize the service.

        Args:
            cache: TTL cache store for persisting fetched content.
            http_client: Async HTTP client for outbound requests.
            max_size_bytes: Max response size; responses larger than this are
                rejected with a :class:`ValueError`.
        """
        self._cache = cache
        self._http_client = http_client
        self._max_size_bytes = max_size_bytes
        self._ttl_seconds = REMOTE_RESOURCE_TTL_HOURS * 3600

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_content(
        self,
        uri: str,
        url: str,
        headers: dict[str, str] | None = None,
    ) -> str:
        """Fetch and cache a single remote resource.

        Returns the cached value when a fresh entry exists, otherwise performs
        an HTTPS GET (with optional ``If-None-Match`` conditional header when an
        ETag is cached) and stores the result.

        Args:
            uri: Logical MCP resource URI used as the cache key discriminator.
            url: Remote HTTPS URL to fetch.
            headers: Optional extra request headers (e.g. Authorization).

        Returns:
            Decoded text content of the resource.

        Raises:
            ValueError: If the URL is not HTTPS, the response is too large,
                or the content-type / extension is not allowed.
            httpx.HTTPError: On network or HTTP-level errors.
        """
        self._assert_https(url)
        cache_key = self._cache_key(uri)

        cached = await self._cache.get(cache_key)
        entry = self._entry_from_cache_value(cached)
        if entry is not None:
            conditional_headers = self._build_conditional_headers(entry)
            if not conditional_headers:
                logger.debug("Cache HIT: uri=%s", uri)
                return entry.content

            # Attempt conditional request
            return await self._conditional_fetch(
                uri=uri,
                url=url,
                cached_entry=entry,
                extra_headers={**(headers or {}), **conditional_headers},
                cache_key=cache_key,
            )
        elif cached is not None:
            logger.warning(
                "Cache entry format invalid for uri=%s; refetching remote resource",
                uri,
            )

        logger.debug("Cache MISS: uri=%s, fetching url=...%s", uri, url[-20:])
        return await self._fetch_and_cache(
            uri=uri, url=url, headers=headers or {}, cache_key=cache_key
        )

    async def get_many(
        self,
        skill_base_uri: str,
        urls: list[str],
        headers: dict[str, str] | None = None,
    ) -> dict[str, str]:
        """Fetch and cache multiple skill resource URLs.

        Each URL is fetched independently using :meth:`get_content`; the
        skill-base URI is extended with each URL's filename as a discriminator.

        Args:
            skill_base_uri: Base URI for the skill (e.g. ``skill://my-skill``).
            urls: List of HTTPS URLs to fetch.
            headers: Optional shared request headers for all requests.

        Returns:
            Dict mapping each URL to its fetched text content.
        """
        results: dict[str, str] = {}
        for url in urls:
            filename = url.rsplit("/", 1)[-1] if "/" in url else url
            uri = f"{skill_base_uri}/{filename}"
            results[url] = await self.get_content(uri=uri, url=url, headers=headers)
        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _cache_key(uri: str) -> str:
        return f"{_CACHE_KEY_PREFIX}:{uri}"

    @staticmethod
    def _assert_https(url: str) -> None:
        """Raise ValueError if url does not use HTTPS (SSRF mitigation)."""
        if not url.startswith("https://"):
            raise ValueError(
                f"Remote resource fetch requires HTTPS URL. Got: {url}"
            )

    @staticmethod
    def _validate_extension(url: str) -> None:
        """Raise ValueError if url file extension is not in the allow-list."""
        from pathlib import PurePosixPath  # noqa: PLC0415
        suffix = PurePosixPath(url.split("?")[0]).suffix.lower()
        if suffix and suffix not in _ALLOWED_EXTENSIONS:
            raise ValueError(
                f"Remote resource has disallowed file extension '{suffix}'. "
                f"Allowed: {sorted(_ALLOWED_EXTENSIONS)}"
            )

    @staticmethod
    def _validate_content_type(content_type: str, url: str) -> None:
        """Raise ValueError if content_type is not in the allow-list."""
        ct_lower = content_type.lower()
        if not any(ct_lower.startswith(prefix) for prefix in _ALLOWED_CONTENT_TYPE_PREFIXES):
            raise ValueError(
                f"Remote resource at '{url}' returned disallowed "
                f"content-type '{content_type}'"
            )

    def _validate_size(self, content: bytes, url: str) -> None:
        """Raise ValueError if content exceeds max_size_bytes."""
        if len(content) > self._max_size_bytes:
            raise ValueError(
                f"Remote resource at '{url}' exceeds maximum size "
                f"({len(content)} > {self._max_size_bytes} bytes)"
            )

    @staticmethod
    def _build_conditional_headers(entry: RemoteResourceEntry) -> dict[str, str]:
        """Build If-None-Match header when a cached ETag is available."""
        if entry.etag:
            return {"If-None-Match": entry.etag}
        return {}

    @staticmethod
    def _entry_to_cache_value(entry: RemoteResourceEntry) -> dict[str, str | None]:
        """Convert typed entry to JSON-serializable cache payload."""
        return {
            "content": entry.content,
            "content_type": entry.content_type,
            "etag": entry.etag,
            "last_modified": entry.last_modified,
        }

    @staticmethod
    def _entry_from_cache_value(value: object | None) -> RemoteResourceEntry | None:
        """Coerce cache payload into a typed entry.

        Supports both the new dict payload format and older in-memory
        ``RemoteResourceEntry`` objects for backward compatibility.
        """
        if value is None:
            return None

        if isinstance(value, RemoteResourceEntry):
            return value

        if not isinstance(value, Mapping):
            return None

        content = value.get("content")
        content_type = value.get("content_type")
        etag = value.get("etag")
        last_modified = value.get("last_modified")

        if not isinstance(content, str) or not isinstance(content_type, str):
            return None
        if etag is not None and not isinstance(etag, str):
            return None
        if last_modified is not None and not isinstance(last_modified, str):
            return None

        return RemoteResourceEntry(
            content=content,
            content_type=content_type,
            etag=etag,
            last_modified=last_modified,
        )

    async def _fetch_and_cache(
        self,
        uri: str,
        url: str,
        headers: dict[str, str],
        cache_key: str,
    ) -> str:
        """Perform an HTTP GET, validate, and store the result in cache."""
        self._validate_extension(url)

        response = await self._http_client.get(
            url,
            headers=headers,
            follow_redirects=False,
        )
        response.raise_for_status()

        content_type = response.headers.get("content-type", "text/plain")
        self._validate_content_type(content_type, url)
        self._validate_size(response.content, url)

        text = response.text
        entry = RemoteResourceEntry(
            content=text,
            content_type=content_type,
            etag=response.headers.get("etag"),
            last_modified=response.headers.get("last-modified"),
        )
        cache_value = self._entry_to_cache_value(entry)
        await self._cache.set(cache_key, cache_value, ttl_seconds=self._ttl_seconds)
        logger.info("Fetched and cached remote resource: uri=%s", uri)
        return text

    async def _conditional_fetch(
        self,
        uri: str,
        url: str,
        cached_entry: RemoteResourceEntry,
        extra_headers: dict[str, str],
        cache_key: str,
    ) -> str:
        """Perform a conditional GET and extend TTL or update cache."""
        self._validate_extension(url)

        try:
            response = await self._http_client.get(
                url,
                headers=extra_headers,
                follow_redirects=False,
            )
        except httpx.HTTPError:
            logger.warning(
                "Conditional fetch failed for uri=%s; serving stale cache", uri
            )
            return cached_entry.content

        if response.status_code == 304:
            # Resource unchanged — extend TTL by re-storing existing entry
            cached_value = self._entry_to_cache_value(cached_entry)
            await self._cache.set(cache_key, cached_value, ttl_seconds=self._ttl_seconds)
            logger.debug("Conditional GET 304 Not Modified: uri=%s, TTL extended", uri)
            return cached_entry.content

        response.raise_for_status()

        content_type = response.headers.get("content-type", "text/plain")
        self._validate_content_type(content_type, url)
        self._validate_size(response.content, url)

        text = response.text
        new_entry = RemoteResourceEntry(
            content=text,
            content_type=content_type,
            etag=response.headers.get("etag"),
            last_modified=response.headers.get("last-modified"),
        )
        new_cache_value = self._entry_to_cache_value(new_entry)
        await self._cache.set(cache_key, new_cache_value, ttl_seconds=self._ttl_seconds)
        logger.info("Conditional fetch refreshed cache: uri=%s", uri)
        return text
