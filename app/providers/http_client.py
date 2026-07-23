"""Shared async HTTP client used by every real provider (Polygon,
Finnhub, SEC EDGAR): rate limiting, retry with exponential backoff, and
a simple in-memory TTL cache. One implementation so rate-limit/retry/
cache behavior is consistent and only needs testing once.

Verification status: this module's logic (backoff timing, cache
expiry, rate-limit spacing) is exercised by
tests/providers/test_http_client.py using a fake transport — no real
network call has been made against it in this sandbox.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional

import httpx

from app.config import Settings


class ProviderError(RuntimeError):
    """Raised when a provider request fails after all retries."""


class RateLimiter:
    """Simple fixed-rate limiter: at most N requests per second, spaced
    evenly rather than bursty. Adequate for REST polling; a real
    production deployment hitting vendor rate limits harder may want a
    proper token-bucket with burst allowance instead."""

    def __init__(self, requests_per_second: float) -> None:
        self._min_interval = 1.0 / requests_per_second if requests_per_second > 0 else 0.0
        self._last_request_at: float = 0.0
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        if self._min_interval <= 0:
            return
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request_at
            remaining = self._min_interval - elapsed
            if remaining > 0:
                await asyncio.sleep(remaining)
            self._last_request_at = time.monotonic()


class TTLCache:
    def __init__(self, ttl_seconds: float) -> None:
        self._ttl = ttl_seconds
        self._store: Dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        if self._ttl <= 0:
            return
        self._store[key] = (time.monotonic() + self._ttl, value)


def _cache_key(url: str, params: Optional[Dict[str, Any]]) -> str:
    if not params:
        return url
    return url + "?" + "&".join(f"{k}={v}" for k, v in sorted(params.items()))


class ResilientHttpClient:
    """Wraps httpx.AsyncClient with rate limiting, retry-with-backoff on
    429/5xx/connection errors, and TTL caching for GET requests."""

    def __init__(self, settings: Settings, base_url: str = "") -> None:
        self._settings = settings
        self._client = httpx.AsyncClient(base_url=base_url, timeout=settings.HTTP_TIMEOUT_SECONDS)
        self._rate_limiter = RateLimiter(settings.HTTP_RATE_LIMIT_PER_SECOND)
        self._cache = TTLCache(settings.HTTP_CACHE_TTL_SECONDS)

    async def get_json(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        use_cache: bool = True,
    ) -> Any:
        key = _cache_key(path, params)
        if use_cache:
            cached = self._cache.get(key)
            if cached is not None:
                return cached

        last_exc: Optional[Exception] = None
        for attempt in range(self._settings.HTTP_MAX_RETRIES + 1):
            await self._rate_limiter.wait()
            try:
                response = await self._client.get(path, params=params, headers=headers)
                if response.status_code == 429 or response.status_code >= 500:
                    raise ProviderError(f"{path} returned {response.status_code}: {response.text[:200]}")
                response.raise_for_status()
                data = response.json()
                if use_cache:
                    self._cache.set(key, data)
                return data
            except (httpx.TransportError, ProviderError) as exc:
                last_exc = exc
                if attempt < self._settings.HTTP_MAX_RETRIES:
                    backoff = self._settings.HTTP_RETRY_BACKOFF_SECONDS * (2 ** attempt)
                    await asyncio.sleep(backoff)
                    continue
                raise ProviderError(f"Failed after {attempt + 1} attempts calling {path}: {exc}") from exc

        # unreachable, but keeps type checkers happy
        raise ProviderError(f"Failed calling {path}: {last_exc}")

    async def aclose(self) -> None:
        await self._client.aclose()
