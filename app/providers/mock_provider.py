"""Synthetic, deterministic data for demonstrating the pipeline only.

THIS IS NOT REAL MARKET DATA, NEWS, OR TRADE HISTORY. No live feed,
broker, or news vendor is connected here — this sandbox has no network
access and no data-vendor credentials. Swap these for real
implementations of the four interfaces in app/providers/base.py to go
live; nothing else in the codebase needs to change to do that.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

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
from app.providers.base import (
    BehavioralDataProvider,
    CorporateEventsProvider,
    HistoricalStatsProvider,
    MarketDataProvider,
    NewsProvider,
)

_DEMO_SYMBOLS = ["ALPH", "BETA", "GAMM", "DLTA", "EPSN"]


class MockMarketDataProvider(MarketDataProvider):
    def __init__(self, seed: int = 7) -> None:
        rng = random.Random(seed)
        self._data: Dict[str, MarketData] = {s: self._synthesize(s, rng) for s in _DEMO_SYMBOLS}

    @staticmethod
    def _synthesize(symbol: str, rng: random.Random) -> MarketData:
        price = round(rng.uniform(3.0, 48.0), 2)
        adv = rng.uniform(500_000, 15_000_000)
        return MarketData(
            symbol=symbol,
            exchange=rng.choice(["NASDAQ", "NYSE", "AMEX"]),
            last_price=price,
            volume=adv * rng.uniform(0.6, 2.5),
            avg_daily_volume=adv,
            avg_daily_dollar_volume=adv * price,
            bid=round(price - 0.01, 2),
            ask=round(price + 0.01, 2),
            spread=0.02,
            relative_volume=round(rng.uniform(0.5, 4.0), 2),
            vwap=round(price * rng.uniform(0.98, 1.02), 3),
            atr=round(price * rng.uniform(0.02, 0.08), 3),
            daily_range=round(price * rng.uniform(0.02, 0.10), 3),
            premarket_change_pct=round(rng.uniform(-5, 8), 2),
            afterhours_change_pct=round(rng.uniform(-3, 3), 2),
            gap_pct=round(rng.uniform(-4, 6), 2),
            float_shares=round(rng.uniform(5_000_000, 80_000_000)),
            shares_outstanding=round(rng.uniform(10_000_000, 120_000_000)),
            market_cap=round(rng.uniform(50_000_000, 3_000_000_000)),
        )

    def get_universe(self) -> List[MarketData]:
        return list(self._data.values())

    def get_market_data(self, symbol: str) -> MarketData:
        return self._data[symbol]


class MockBehavioralDataProvider(BehavioralDataProvider):
    """Stands in for reading the bpm-python receiver's /state/latest
    endpoint for each symbol."""

    def __init__(self, seed: int = 11) -> None:
        self._rng = random.Random(seed)

    def get_behavioral_data(self, symbol: str) -> Optional[BehavioralData]:
        forecast_bias = self._rng.choice([
            "Continuation Bias", "Compression Bias", "Negotiation Bias", "Neutral", None,
        ])
        return BehavioralData(
            confirmed_state=self._rng.choice(["Expansion", "Negotiation", "Compression"]),
            confirmed_direction=self._rng.choice(["Bullish", "Bearish", "Neutral"]),
            bo_status=self._rng.choice(["Confirmed", "Confirming", "NO_CYCLE"]),
            mc_status=self._rng.choice(["Provisional", "Locked", "None"]),
            pressure_efficiency=round(self._rng.uniform(20, 90), 1),
            acceptance_status=self._rng.choice(["Strong", "Moderate", "Weak", "Testing", "Failed"]),
            bes_scenario=self._rng.choice([
                "BES-1 Origin (BO-MCZ)", "BES-2 Momentum (MCZ-RZ)", "BES-3 Recovery (RZ-BE)",
            ]),
            forecast_bias=forecast_bias,
            bars_in_confirmed_state=self._rng.choice([None, self._rng.randint(1, 30)]),
            recent_transition_count=self._rng.choice([None, self._rng.randint(0, 5)]),
        )


class MockCorporateEventsProvider(CorporateEventsProvider):
    """Synthetic SEC filings, earnings, insider transactions, and analyst
    revisions — NOT real filings. Notice that transaction_type below uses
    literal SEC Form 4 terminology ("Buy"/"Sell"), because that's what a
    real filing says; see describe_insider_transaction() in
    app/models/snapshot.py for how this gets neutralized before it can
    reach any screener output text."""

    def __init__(self, seed: int = 19) -> None:
        self._rng = random.Random(seed)

    def get_sec_filings(self, symbol: str) -> List[SECFiling]:
        if self._rng.random() < 0.4:
            return []
        return [SECFiling(
            timestamp=datetime.now(timezone.utc) - timedelta(days=self._rng.randint(1, 60)),
            filing_type=self._rng.choice(["10-K", "10-Q", "8-K"]),
            headline=f"{symbol}: sample filing headline (mock data)",
        )]

    def get_earnings_events(self, symbol: str) -> List[EarningsEvent]:
        if self._rng.random() < 0.5:
            return []
        eps_est = round(self._rng.uniform(-0.5, 2.0), 2)
        eps_act = round(eps_est + self._rng.uniform(-0.3, 0.3), 2)
        return [EarningsEvent(
            timestamp=datetime.now(timezone.utc) - timedelta(days=self._rng.randint(0, 90)),
            eps_actual=eps_act,
            eps_estimate=eps_est,
            surprise_pct=round((eps_act - eps_est) / abs(eps_est) * 100.0, 1) if eps_est else None,
            reaction_pct=round(self._rng.uniform(-15, 15), 1),
        )]

    def get_insider_transactions(self, symbol: str) -> List[InsiderTransaction]:
        if self._rng.random() < 0.6:
            return []
        return [InsiderTransaction(
            timestamp=datetime.now(timezone.utc) - timedelta(days=self._rng.randint(1, 30)),
            insider_role=self._rng.choice(["CEO", "CFO", "Director", "10% Owner"]),
            transaction_type=self._rng.choice(["Buy", "Sell"]),
            shares=round(self._rng.uniform(1000, 50000)),
            value_estimate=round(self._rng.uniform(10_000, 2_000_000), 2),
        )]

    def get_analyst_revisions(self, symbol: str) -> List[AnalystRevision]:
        if self._rng.random() < 0.5:
            return []
        return [AnalystRevision(
            timestamp=datetime.now(timezone.utc) - timedelta(days=self._rng.randint(1, 14)),
            firm=self._rng.choice(["Sample Capital", "Mock & Co.", "Synthetic Partners"]),
            action=self._rng.choice(["Upgrade", "Downgrade", "Initiate", "Reiterate"]),
            price_target=round(self._rng.uniform(5, 60), 2),
        )]


class MockNewsProvider(NewsProvider):
    def __init__(self, seed: int = 13) -> None:
        self._rng = random.Random(seed)

    def get_news(self, symbol: str) -> List[NewsItem]:
        count = self._rng.randint(0, 2)
        items: List[NewsItem] = []
        for i in range(count):
            impact = self._rng.choice(["Supportive", "Conflicting", "Neutral"])
            items.append(
                NewsItem(
                    timestamp=datetime.now(timezone.utc) - timedelta(hours=self._rng.randint(1, 48)),
                    source=self._rng.choice(["Company PR", "SEC Filing", "Analyst Note"]),
                    headline=f"{symbol}: sample headline #{i + 1} (mock data)",
                    summary="Synthetic summary for demonstration only — not real news.",
                    relevance=round(self._rng.uniform(0.3, 1.0), 2),
                    estimated_behavioral_impact=impact,
                    confidence=round(self._rng.uniform(0.4, 0.9), 2),
                )
            )
        return items


class MockHistoricalStatsProvider(HistoricalStatsProvider):
    def __init__(self, seed: int = 17) -> None:
        self._rng = random.Random(seed)

    def get_historical_stats(self, symbol: str, condition_key: str) -> Optional[HistoricalStats]:
        occurrences = self._rng.randint(0, 40)
        if occurrences == 0:
            return HistoricalStats(occurrences=0)
        win_rate = round(self._rng.uniform(0.3, 0.7), 3)
        return HistoricalStats(
            occurrences=occurrences,
            win_rate=win_rate,
            loss_rate=round(1.0 - win_rate, 3),
            avg_r=round(self._rng.uniform(-0.3, 1.2), 2),
            median_r=round(self._rng.uniform(-0.2, 1.0), 2),
            profit_factor=round(self._rng.uniform(0.7, 2.2), 2),
            avg_hold_bars=round(self._rng.uniform(3, 40), 1),
            max_drawdown=round(self._rng.uniform(0.5, 3.0), 2),
            mfe=round(self._rng.uniform(0.5, 3.0), 2),
            mae=round(self._rng.uniform(0.3, 2.0), 2),
            confidence_interval_95=(max(0.0, round(win_rate - 0.15, 3)), min(1.0, round(win_rate + 0.15, 3))),
        )
