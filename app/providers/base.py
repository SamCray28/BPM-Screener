"""Provider-agnostic interfaces. Changing vendors must never require
changes to any engine — every engine in app/engines depends only on
these interfaces and the data models in app/models/snapshot.py.
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
    TimeframeSeries,
)


class MarketDataProvider(ABC):
    @abstractmethod
    async def get_universe(self) -> List[MarketData]:
        """Return current MarketData for every symbol this provider covers,
        already filtered to active U.S. equities by the provider itself
        where the vendor API supports that filter natively."""

    @abstractmethod
    async def get_market_data(self, symbol: str) -> MarketData:
        ...

    @abstractmethod
    async def get_bars(self, symbol: str, timeframe: str, limit: int = 200) -> TimeframeSeries:
        """timeframe uses Pine-style strings: '1','5','15','60','240','D'."""

    @abstractmethod
    async def stream_quotes(self, symbols: List[str]):
        """Async generator yielding MarketData updates as they arrive over
        a live connection (e.g. WebSocket). Implementations must handle
        their own reconnect/backoff internally."""


class NewsProvider(ABC):
    @abstractmethod
    async def get_news(self, symbol: str) -> List[NewsItem]:
        ...


class CorporateEventsProvider(ABC):
    @abstractmethod
    async def get_sec_filings(self, symbol: str) -> List[SECFiling]:
        ...

    @abstractmethod
    async def get_earnings_events(self, symbol: str) -> List[EarningsEvent]:
        ...

    @abstractmethod
    async def get_insider_transactions(self, symbol: str) -> List[InsiderTransaction]:
        ...

    @abstractmethod
    async def get_analyst_revisions(self, symbol: str) -> List[AnalystRevision]:
        ...


class HistoricalStatsProvider(ABC):
    @abstractmethod
    async def get_historical_stats(self, symbol: str, condition_key: str) -> Optional[HistoricalStats]:
        """condition_key: 'state|direction|bes_scenario'."""


class BehavioralDataProvider(ABC):
    """Bridges to BPM's Pine telemetry — reads the latest confirmed
    telemetry event for a symbol. Must never recompute BO/MC/state
    itself; Pine remains the source of truth."""

    @abstractmethod
    async def get_behavioral_data(self, symbol: str) -> Optional[BehavioralData]:
        ...


class SentimentProvider(ABC):
    """Distinct from NewsProvider: this classifies attention/sentiment
    signals that may not be individual news items (social volume,
    unusual-options-activity proxies, etc.) — see the spec's Sentiment
    Engine section. Currently only a rule-based text classifier is
    implemented; real social/options sentiment needs a real vendor."""

    @abstractmethod
    async def classify_text(self, text: str) -> tuple[str, float]:
        """Returns (label, confidence) where label is 'Positive' |
        'Negative' | 'Neutral'."""
