"""Selects mock or real provider implementations based on Settings, so
routes/scheduler code never has to know which vendor (or mock) is in
use — exactly the interchangeability the brief asks for. Defaults to
mock everywhere; a real provider only activates when its *_PROVIDER
setting is switched and its API key is present.
"""
from __future__ import annotations

from app.config import Settings
from app.providers.base import (
    BehavioralDataProvider,
    CorporateEventsProvider,
    HistoricalStatsProvider,
    MarketDataProvider,
    NewsProvider,
    SentimentProvider,
)
from app.providers.mock.mock_providers import (
    MockBehavioralDataProvider,
    MockCorporateEventsProvider,
    MockHistoricalStatsProvider,
    MockMarketDataProvider,
    MockNewsProvider,
    MockSentimentProvider,
)


def build_market_data_provider(settings: Settings) -> MarketDataProvider:
    if settings.MARKET_DATA_PROVIDER == "polygon" and settings.POLYGON_API_KEY:
        from app.providers.polygon_market_data import PolygonMarketDataProvider
        return PolygonMarketDataProvider(settings)
    return MockMarketDataProvider()


def build_news_provider(settings: Settings) -> NewsProvider:
    if settings.NEWS_PROVIDER == "polygon" and settings.POLYGON_API_KEY:
        from app.providers.polygon_news import PolygonNewsProvider
        return PolygonNewsProvider(settings)
    return MockNewsProvider()


def build_corporate_events_provider(settings: Settings) -> CorporateEventsProvider:
    if settings.CORPORATE_EVENTS_PROVIDER == "finnhub" and settings.FINNHUB_API_KEY:
        from app.providers.finnhub_corporate_events import FinnhubCorporateEventsProvider
        return FinnhubCorporateEventsProvider(settings)
    return MockCorporateEventsProvider()


def build_sentiment_provider(settings: Settings) -> SentimentProvider:
    if settings.SENTIMENT_PROVIDER == "rule_based":
        from app.providers.sentiment_provider import RuleBasedSentimentProvider
        return RuleBasedSentimentProvider()
    return MockSentimentProvider()


def build_historical_stats_provider(settings: Settings, session) -> HistoricalStatsProvider:
    if settings.APP_ENV == "production":
        from app.providers.db_historical_stats import SQLAlchemyHistoricalStatsProvider
        return SQLAlchemyHistoricalStatsProvider(session)
    return MockHistoricalStatsProvider()


def build_behavioral_data_provider(settings: Settings, session) -> BehavioralDataProvider:
    if settings.APP_ENV == "production":
        from app.providers.db_behavioral_data import DatabaseBehavioralDataProvider
        return DatabaseBehavioralDataProvider(session)
    return MockBehavioralDataProvider()
