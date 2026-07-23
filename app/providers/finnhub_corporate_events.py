"""Finnhub corporate events provider (https://finnhub.io/docs/api).
Covers earnings surprises, insider transactions, and analyst
upgrade/downgrade actions — SEC filings are handled separately by
sec_edgar_filings.py since EDGAR is the authoritative free source for
those.

Endpoints used (per Finnhub's public docs as of my training):
- GET /stock/earnings?symbol=SYM&token=...            (EPS surprise history)
- GET /stock/insider-transactions?symbol=SYM&token=... (Form-4-derived transactions)
- GET /stock/upgrade-downgrade?symbol=SYM&token=...    (analyst rating actions)

Verification status: the parse_* functions this provider uses (in
app/providers/parsers.py) are pure and unit-tested against realistic
mock JSON in tests/unit/test_provider_parsers.py. The HTTP-fetching
methods here have not been exercised against the live Finnhub API in
this sandbox — no network access, no API key.
"""
from __future__ import annotations

from typing import List

from app.config import Settings
from app.models.snapshot import AnalystRevision, EarningsEvent, InsiderTransaction
from app.providers.base import CorporateEventsProvider
from app.providers.http_client import ResilientHttpClient
from app.providers.parsers import parse_analyst_revision, parse_earnings_event, parse_insider_transaction
from app.providers.sec_edgar_filings import SecEdgarFilingsMixin


class FinnhubCorporateEventsProvider(CorporateEventsProvider, SecEdgarFilingsMixin):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._http = ResilientHttpClient(settings, base_url=settings.FINNHUB_BASE_URL)
        SecEdgarFilingsMixin.__init__(self, settings)

    async def get_earnings_events(self, symbol: str) -> List[EarningsEvent]:
        data = await self._http.get_json(
            "/stock/earnings", params={"symbol": symbol, "token": self._settings.FINNHUB_API_KEY},
        )
        return [parse_earnings_event(r) for r in data or []]

    async def get_insider_transactions(self, symbol: str) -> List[InsiderTransaction]:
        data = await self._http.get_json(
            "/stock/insider-transactions", params={"symbol": symbol, "token": self._settings.FINNHUB_API_KEY},
        )
        return [parse_insider_transaction(r) for r in data.get("data", [])]

    async def get_analyst_revisions(self, symbol: str) -> List[AnalystRevision]:
        data = await self._http.get_json(
            "/stock/upgrade-downgrade", params={"symbol": symbol, "token": self._settings.FINNHUB_API_KEY},
        )
        return [parse_analyst_revision(r) for r in data or []]

    async def aclose(self) -> None:
        await self._http.aclose()
