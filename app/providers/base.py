"""Provider-agnostic data interfaces.

The spec explicitly requires the architecture be swappable across data
vendors without rewriting the system. Nothing under app/engines or
app/models depends on a specific vendor — only these four interfaces
need a real implementation (e.g. Polygon/IEX/Databento for market data,
a news/SEC-filing API for NewsProvider, your own trade journal or
research database for HistoricalStatsProvider, and the bpm-python
receiver's /state/latest endpoint for BehavioralDataProvider) to take
this from demo to production.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from app.models.snapshot import (
    AnalystRevision,
    BehavioralData,
    EarningsEvent,
    HistoricalStats,
    InsiderTransaction,
    MarketData,
    NewsItem,
    SECFiling,
)


class MarketDataProvider(ABC):
    @abstractmethod
    def get_universe(self) -> List[MarketData]:
        """Return current MarketData for every symbol this provider covers."""

    @abstractmethod
    def get_market_data(self, symbol: str) -> MarketData:
        ...


class BehavioralDataProvider(ABC):
    """Bridges to BPM's Pine telemetry (e.g. by reading the bpm-python
    receiver's GET /state/latest endpoint per symbol). Must never
    recompute BO/MC/state itself — Pine remains the source of truth."""

    @abstractmethod
    def get_behavioral_data(self, symbol: str) -> Optional[BehavioralData]:
        ...


class NewsProvider(ABC):
    @abstractmethod
    def get_news(self, symbol: str) -> List[NewsItem]:
        ...


class HistoricalStatsProvider(ABC):
    @abstractmethod
    def get_historical_stats(self, symbol: str, condition_key: str) -> Optional[HistoricalStats]:
        """condition_key identifies the recurring behavioral condition being
        tracked, e.g. 'Expansion|Bullish|BES-2 Momentum (MCZ-RZ)'."""


class CorporateEventsProvider(ABC):
    """SEC filings, earnings, insider transactions, and analyst revisions —
    the "Institutional Data Layer" items beyond live quotes and headline
    news. Level II and options flow are explicitly out of scope per the
    spec's own "(future)" markers and have no interface here yet."""

    @abstractmethod
    def get_sec_filings(self, symbol: str) -> List[SECFiling]:
        ...

    @abstractmethod
    def get_earnings_events(self, symbol: str) -> List[EarningsEvent]:
        ...

    @abstractmethod
    def get_insider_transactions(self, symbol: str) -> List[InsiderTransaction]:
        ...

    @abstractmethod
    def get_analyst_revisions(self, symbol: str) -> List[AnalystRevision]:
        ...
