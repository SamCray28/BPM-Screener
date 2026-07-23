"""SEC EDGAR filings provider (https://www.sec.gov/edgar/sec-api-documentation).
Free and public — no API key required, but SEC requires a descriptive
User-Agent header identifying the requester (SEC_EDGAR_USER_AGENT).

Two-step lookup: ticker -> CIK via the published company_tickers.json
mapping, then CIK -> recent filings via the submissions endpoint.

Verification status: `parse_recent_filings` is a pure function tested
against a realistic mock submissions JSON shape in
tests/providers/test_sec_edgar_parsing.py. The HTTP-fetching methods
have not been exercised against the live SEC API in this sandbox — no
network access here. SEC's rate limit (documented as ~10 req/sec) is
respected via the shared ResilientHttpClient's rate limiter, but that
hasn't been validated against a real SEC response either.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from app.config import Settings
from app.models.snapshot import SECFiling
from app.providers.http_client import ResilientHttpClient
from app.providers.parsers import parse_recent_filings


class SecEdgarFilingsMixin:
    """Mixin providing get_sec_filings(); mixed into
    FinnhubCorporateEventsProvider so one CorporateEventsProvider
    implementation covers all four data types even though filings come
    from a different (free) source than earnings/insider/analyst data."""

    def __init__(self, settings: Settings) -> None:
        self._sec_settings = settings
        self._sec_http = ResilientHttpClient(settings, base_url=settings.SEC_EDGAR_BASE_URL)
        self._cik_cache: Optional[Dict[str, str]] = None

    async def _resolve_cik(self, symbol: str) -> Optional[str]:
        if self._cik_cache is None:
            # Served from www.sec.gov, not data.sec.gov — a separate host,
            # fetched once and cached for the life of the provider.
            client = ResilientHttpClient(self._sec_settings, base_url="https://www.sec.gov")
            try:
                data = await client.get_json(
                    "/files/company_tickers.json",
                    headers={"User-Agent": self._sec_settings.SEC_EDGAR_USER_AGENT},
                )
                self._cik_cache = {
                    entry["ticker"].upper(): str(entry["cik_str"]).zfill(10)
                    for entry in data.values()
                }
            finally:
                await client.aclose()
        return self._cik_cache.get(symbol.upper())

    async def get_sec_filings(self, symbol: str) -> List[SECFiling]:
        cik = await self._resolve_cik(symbol)
        if cik is None:
            return []
        data = await self._sec_http.get_json(
            f"/submissions/CIK{cik}.json",
            headers={"User-Agent": self._sec_settings.SEC_EDGAR_USER_AGENT},
        )
        return parse_recent_filings(data)
