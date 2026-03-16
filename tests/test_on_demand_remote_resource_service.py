"""Tests for OnDemandRemoteResourceService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from drunk_ai_proxy.proxies.resource.on_demand_remote_resource_service import (
    OnDemandRemoteResourceService,
    RemoteResourceEntry,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def cache():
    """Return a mock TTLAsyncKeyValue cache store."""
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock()
    return mock


@pytest.fixture()
def http_client():
    """Return a mock httpx.AsyncClient."""
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.fixture()
def service(cache, http_client):
    """Return a configured OnDemandRemoteResourceService."""
    return OnDemandRemoteResourceService(cache=cache, http_client=http_client)


def _make_response(
    status_code: int = 200,
    text: str = "# Hello",
    content_type: str = "text/markdown",
    etag: str | None = None,
    last_modified: str | None = None,
) -> MagicMock:
    """Build a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.text = text
    resp.content = text.encode()
    headers: dict[str, str] = {"content-type": content_type}
    if etag:
        headers["etag"] = etag
    if last_modified:
        headers["last-modified"] = last_modified
    resp.headers = headers
    resp.raise_for_status = MagicMock()
    return resp


# ---------------------------------------------------------------------------
# TestGetContentCacheMiss
# ---------------------------------------------------------------------------


class TestGetContentCacheMiss:
    """Tests for get_content when the cache is empty (cold path)."""

    @pytest.mark.asyncio
    async def test_fetches_url_and_returns_content(self, service, cache, http_client):
        url = "https://example.com/SKILL.md"
        http_client.get = AsyncMock(return_value=_make_response())
        cache.get = AsyncMock(return_value=None)

        result = await service.get_content(uri="skill://test", url=url)

        assert result == "# Hello"
        http_client.get.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_stores_entry_in_cache(self, service, cache, http_client):
        url = "https://example.com/SKILL.md"
        http_client.get = AsyncMock(return_value=_make_response(etag='"abc123"'))
        cache.get = AsyncMock(return_value=None)

        await service.get_content(uri="skill://test", url=url)

        cache.set.assert_awaited_once()
        args = cache.set.call_args
        entry = args[0][1]
        assert isinstance(entry, dict)
        assert entry.get("etag") == '"abc123"'

    @pytest.mark.asyncio
    async def test_raises_on_http_url(self, service, cache):
        with pytest.raises(ValueError, match="HTTPS"):
            await service.get_content(
                uri="skill://test", url="http://example.com/SKILL.md"
            )

    @pytest.mark.asyncio
    async def test_raises_on_disallowed_extension(self, service, cache, http_client):
        url = "https://example.com/malware.exe"
        cache.get = AsyncMock(return_value=None)
        with pytest.raises(ValueError, match="extension"):
            await service.get_content(uri="skill://test", url=url)

    @pytest.mark.asyncio
    async def test_raises_on_disallowed_content_type(self, service, cache, http_client):
        url = "https://example.com/payload.md"
        http_client.get = AsyncMock(
            return_value=_make_response(content_type="application/octet-stream")
        )
        cache.get = AsyncMock(return_value=None)
        with pytest.raises(ValueError, match="content-type"):
            await service.get_content(uri="skill://test", url=url)

    @pytest.mark.asyncio
    async def test_raises_when_response_too_large(self, service, cache, http_client):
        url = "https://example.com/SKILL.md"
        huge = "x" * (11 * 1024 * 1024)
        http_client.get = AsyncMock(return_value=_make_response(text=huge))
        cache.get = AsyncMock(return_value=None)
        with pytest.raises(ValueError, match="size"):
            await service.get_content(uri="skill://test", url=url)

    @pytest.mark.asyncio
    async def test_passes_extra_headers_to_client(self, service, cache, http_client):
        url = "https://example.com/SKILL.md"
        http_client.get = AsyncMock(return_value=_make_response())
        cache.get = AsyncMock(return_value=None)
        extra = {"Authorization": "Bearer tok"}

        await service.get_content(uri="skill://test", url=url, headers=extra)

        _, call_kwargs = http_client.get.call_args
        sent_headers = call_kwargs.get("headers") or http_client.get.call_args[1]["headers"]
        assert "Authorization" in sent_headers


# ---------------------------------------------------------------------------
# TestGetContentCacheHit
# ---------------------------------------------------------------------------


class TestGetContentCacheHit:
    """Tests for get_content when a fresh cache entry exists."""

    @pytest.mark.asyncio
    async def test_returns_cached_content_without_fetching(self, service, cache, http_client):
        """When cached entry has no ETag, return content without any outbound call."""
        url = "https://example.com/SKILL.md"
        cached_entry = RemoteResourceEntry(content="cached content", content_type="text/markdown")
        cache.get = AsyncMock(return_value=cached_entry)

        result = await service.get_content(uri="skill://test", url=url)

        assert result == "cached content"
        http_client.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_uses_if_none_match_when_etag_present(self, service, cache, http_client):
        """When cached entry has ETag, a conditional GET should be issued."""
        url = "https://example.com/SKILL.md"
        cached_entry = RemoteResourceEntry(
            content="old content",
            content_type="text/markdown",
            etag='"v1"',
        )
        cache.get = AsyncMock(return_value=cached_entry)
        http_client.get = AsyncMock(return_value=_make_response(status_code=304))

        result = await service.get_content(uri="skill://test", url=url)

        assert result == "old content"
        _, call_kwargs = http_client.get.call_args
        sent = call_kwargs.get("headers") or http_client.get.call_args[1]["headers"]
        assert sent.get("If-None-Match") == '"v1"'

    @pytest.mark.asyncio
    async def test_304_extends_ttl_in_cache(self, service, cache, http_client):
        """304 responses should re-store the existing entry to extend its TTL."""
        url = "https://example.com/SKILL.md"
        cached_entry = RemoteResourceEntry(
            content="old content",
            content_type="text/markdown",
            etag='"v1"',
        )
        cache.get = AsyncMock(return_value=cached_entry)
        http_client.get = AsyncMock(return_value=_make_response(status_code=304))

        await service.get_content(uri="skill://test", url=url)

        cache.set.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_200_on_conditional_request_updates_cache(self, service, cache, http_client):
        """A 200 response during conditional fetch stores fresh entry."""
        url = "https://example.com/SKILL.md"
        cached_entry = RemoteResourceEntry(
            content="old content",
            content_type="text/markdown",
            etag='"v1"',
        )
        cache.get = AsyncMock(return_value=cached_entry)
        http_client.get = AsyncMock(
            return_value=_make_response(text="new content", etag='"v2"')
        )

        result = await service.get_content(uri="skill://test", url=url)

        assert result == "new content"
        cache.set.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_conditional_fetch_error_serves_stale(self, service, cache, http_client):
        """Network error during conditional fetch should return cached content."""
        url = "https://example.com/SKILL.md"
        cached_entry = RemoteResourceEntry(
            content="stale content",
            content_type="text/markdown",
            etag='"v1"',
        )
        cache.get = AsyncMock(return_value=cached_entry)
        http_client.get = AsyncMock(side_effect=httpx.ConnectError("timeout"))

        result = await service.get_content(uri="skill://test", url=url)

        # Stale-on-error: cached content returned
        assert result == "stale content"


# ---------------------------------------------------------------------------
# TestStaticHelpers
# ---------------------------------------------------------------------------


class TestStaticHelpers:
    """Tests for static validation helper methods."""

    def test_assert_https_raises_for_http(self):
        with pytest.raises(ValueError, match="HTTPS"):
            OnDemandRemoteResourceService._assert_https("http://example.com/x.md")

    def test_assert_https_passes_for_https(self):
        OnDemandRemoteResourceService._assert_https("https://example.com/x.md")

    def test_validate_extension_rejects_disallowed(self):
        with pytest.raises(ValueError, match="extension"):
            OnDemandRemoteResourceService._validate_extension("https://x.com/exec.bin")

    def test_validate_extension_accepts_md(self):
        OnDemandRemoteResourceService._validate_extension("https://x.com/SKILL.md")

    def test_validate_extension_accepts_yaml(self):
        OnDemandRemoteResourceService._validate_extension("https://x.com/config.yaml")

    def test_validate_extension_no_suffix_passes(self):
        # Files with no suffix are not rejected
        OnDemandRemoteResourceService._validate_extension("https://x.com/SKILL")

    def test_validate_content_type_rejects_binary(self):
        with pytest.raises(ValueError, match="content-type"):
            OnDemandRemoteResourceService._validate_content_type(
                "application/octet-stream", "https://x.com/x"
            )

    def test_validate_content_type_accepts_text_markdown(self):
        OnDemandRemoteResourceService._validate_content_type(
            "text/markdown; charset=utf-8", "https://x.com/x.md"
        )

    def test_validate_content_type_accepts_application_json(self):
        OnDemandRemoteResourceService._validate_content_type(
            "application/json", "https://x.com/x.json"
        )

    def test_build_conditional_headers_with_etag(self):
        entry = RemoteResourceEntry(content="x", content_type="text/plain", etag='"v1"')
        headers = OnDemandRemoteResourceService._build_conditional_headers(entry)
        assert headers == {"If-None-Match": '"v1"'}

    def test_build_conditional_headers_without_etag(self):
        entry = RemoteResourceEntry(content="x", content_type="text/plain")
        headers = OnDemandRemoteResourceService._build_conditional_headers(entry)
        assert headers == {}


# ---------------------------------------------------------------------------
# TestGetMany
# ---------------------------------------------------------------------------


class TestGetMany:
    """Tests for the multi-fetch get_many helper."""

    @pytest.mark.asyncio
    async def test_fetches_all_urls(self, service, cache, http_client):
        urls = [
            "https://example.com/SKILL.md",
            "https://example.com/helper.py",
        ]
        call_count = 0

        async def _mock_get(url: str, **kwargs):  # noqa: ANN001
            nonlocal call_count
            call_count += 1
            return _make_response(text=f"content:{url.rsplit('/', 1)[-1]}")

        http_client.get = _mock_get
        cache.get = AsyncMock(return_value=None)

        result = await service.get_many(
            skill_base_uri="skill://my-skill", urls=urls
        )

        assert call_count == 2
        assert result[urls[0]] == "content:SKILL.md"
        assert result[urls[1]] == "content:helper.py"
