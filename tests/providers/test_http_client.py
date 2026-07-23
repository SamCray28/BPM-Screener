"""Tests for app/providers/http_client.py using httpx's MockTransport,
so retry/backoff/caching logic is exercised without any real network
call. Requires httpx to be installed — this sandbox has no network
access to install it, so these have NOT been executed here. They are
designed to run in CI (see .github/workflows/ci.yml) where dependencies
are actually installed.
"""
import asyncio

import httpx
import pytest

from app.config import Settings
from app.providers.http_client import ProviderError, ResilientHttpClient, TTLCache


def _settings(**overrides) -> Settings:
    base = dict(
        HTTP_TIMEOUT_SECONDS=1.0, HTTP_MAX_RETRIES=2, HTTP_RETRY_BACKOFF_SECONDS=0.01,
        HTTP_RATE_LIMIT_PER_SECOND=1000.0, HTTP_CACHE_TTL_SECONDS=5.0,
    )
    base.update(overrides)
    return Settings(**base)


@pytest.mark.asyncio
async def test_successful_request_returns_json():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True})

    client = ResilientHttpClient(_settings(), base_url="https://example.test")
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://example.test")

    result = await client.get_json("/thing")
    assert result == {"ok": True}
    await client.aclose()


@pytest.mark.asyncio
async def test_retries_on_500_then_succeeds():
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] < 3:
            return httpx.Response(500, text="server error")
        return httpx.Response(200, json={"ok": True})

    client = ResilientHttpClient(_settings(HTTP_MAX_RETRIES=3), base_url="https://example.test")
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://example.test")

    result = await client.get_json("/thing", use_cache=False)
    assert result == {"ok": True}
    assert calls["count"] == 3
    await client.aclose()


@pytest.mark.asyncio
async def test_raises_provider_error_after_exhausting_retries():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="still broken")

    client = ResilientHttpClient(_settings(HTTP_MAX_RETRIES=1, HTTP_RETRY_BACKOFF_SECONDS=0.01), base_url="https://example.test")
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://example.test")

    with pytest.raises(ProviderError):
        await client.get_json("/thing", use_cache=False)
    await client.aclose()


def test_ttl_cache_expires():
    cache = TTLCache(ttl_seconds=0.01)
    cache.set("k", "v")
    assert cache.get("k") == "v"
    import time
    time.sleep(0.02)
    assert cache.get("k") is None


def test_ttl_cache_disabled_when_ttl_zero():
    cache = TTLCache(ttl_seconds=0)
    cache.set("k", "v")
    assert cache.get("k") is None
