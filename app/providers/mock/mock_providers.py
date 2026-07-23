"""Synthetic, deterministic async mock providers implementing all 6
provider interfaces. THIS IS NOT REAL DATA — no live feed, broker,
news, or filings vendor is connected. Used for local development,
tests, and the demo; swap for the real providers in app/providers/
once API keys and a live database are available.
"""
from __future__ import annotations

import asyncio
import random
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator, List, Optional, Tuple

from app.models.snapshot import (
    AnalystRevision,
    Bar,
    BehavioralData,
    EarningsEvent,
    HistoricalStats,
    InsiderTransaction,
    MarketData,
    NewsItem,
    SECFiling,
    TimeframeSeries,
)
from app.providers.base import (
    BehavioralDataProvider,
    CorporateEventsProvider,
    HistoricalStatsProvider,
    MarketDataProvider,
    NewsProvider,
    SentimentProvider,
)

_DEMO_SYMBOLS = ["ALPH", "BETA", "GAMM", "DLTA", "EPSN"]
_TIMEFRAMES = ["1", "5", "15", "60", "240", "D"]


class MockMarketDataProvider(MarketDataProvider):
    def __init__(self, seed: int = 7) -> None:
        rng = random.Random(seed)
        self._data = {s: self._synthesize(s, rng) for s in _DEMO_SYMBOLS}

    @staticmethod
    def _synthesize(symbol: str, rng: random.Random) -> MarketData:
        price = round(rng.uniform(3.0, 48.0), 2)
        adv = rng.uniform(500_000, 15_000_000)
        return MarketData(
            symbol=symbol, exchange=rng.choice(["NASDAQ", "NYSE", "AMEX"]), last_price=price,
            volume=adv * rng.uniform(0.6, 2.5), avg_daily_volume=adv, avg_daily_dollar_volume=adv * price,
            timestamp=datetime.now(timezone.utc),
            bid=round(price - 0.01, 2), ask=round(price + 0.01, 2), spread=0.02,
            relative_volume=round(rng.uniform(0.5, 4.0), 2), vwap=round(price * rng.uniform(0.98, 1.02), 3),
            atr=round(price * rng.uniform(0.02, 0.08), 3), daily_range=round(price * rng.uniform(0.02, 0.10), 3),
            premarket_change_pct=round(rng.uniform(-5, 8), 2), afterhours_change_pct=round(rng.uniform(-3, 3), 2),
            gap_pct=round(rng.uniform(-4, 6), 2), float_shares=round(rng.uniform(5_000_000, 80_000_000)),
            shares_outstanding=round(rng.uniform(10_000_000, 120_000_000)),
            market_cap=round(rng.uniform(50_000_000, 3_000_000_000)),
            halt_status=rng.choice(["Trading", "Trading", "Trading", "Halted"]),
        )

    async def get_universe(self) -> List[MarketData]:
        return list(self._data.values())

    async def get_market_data(self, symbol: str) -> MarketData:
        return self._data[symbol]

    async def get_bars(self, symbol: str, timeframe: str, limit: int = 200) -> TimeframeSeries:
        rng = random.Random(hash((symbol, timeframe)) & 0xFFFFFFFF)
        price = self._data.get(symbol, self._synthesize(symbol, rng)).last_price
        bars: List[Bar] = []
        now = datetime.now(timezone.utc)
        step_minutes = {"1": 1, "5": 5, "15": 15, "60": 60, "240": 240, "D": 1440}.get(timeframe, 5)
        for i in range(limit, 0, -1):
            drift = rng.uniform(-0.01, 0.01) * price
            o = price + drift
            h = o + abs(rng.uniform(0, 0.01)) * price
            l = o - abs(rng.uniform(0, 0.01)) * price
            c = rng.uniform(l, h)
            bars.append(Bar(
                timestamp=now - timedelta(minutes=step_minutes * i),
                open=round(o, 3), high=round(h, 3), low=round(l, 3), close=round(c, 3),
                volume=rng.uniform(10_000, 200_000),
            ))
            price = c
        return TimeframeSeries(timeframe=timeframe, bars=bars)

    async def stream_quotes(self, symbols: List[str]) -> AsyncGenerator[MarketData, None]:
        rng = random.Random(23)
        while True:
            for symbol in symbols:
                await asyncio.sleep(0)  # yield control; a real stream has no sleep here, this is synthetic pacing
                base = self._data.get(symbol)
                if base is None:
                    continue
                jitter = rng.uniform(-0.05, 0.05)
                yield MarketData(
                    symbol=symbol, exchange=base.exchange, last_price=round(base.last_price + jitter, 2),
                    volume=base.volume, avg_daily_volume=base.avg_daily_volume,
                    avg_daily_dollar_volume=base.avg_daily_dollar_volume, timestamp=datetime.now(timezone.utc),
                )
            return  # mock stream terminates after one pass; a real one never returns


class MockBehavioralDataProvider(BehavioralDataProvider):
    def __init__(self, seed: int = 11) -> None:
        self._rng = random.Random(seed)

    async def get_behavioral_data(self, symbol: str) -> Optional[BehavioralData]:
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
            forecast_bias=self._rng.choice([
                "Continuation Bias", "Compression Bias", "Negotiation Bias", "Neutral", None,
            ]),
            bars_in_confirmed_state=self._rng.choice([None, self._rng.randint(1, 30)]),
            recent_transition_count=self._rng.choice([None, self._rng.randint(0, 5)]),
        )


class MockNewsProvider(NewsProvider):
    def __init__(self, seed: int = 13) -> None:
        self._rng = random.Random(seed)

    async def get_news(self, symbol: str) -> List[NewsItem]:
        count = self._rng.randint(0, 2)
        items = []
        for i in range(count):
            items.append(NewsItem(
                timestamp=datetime.now(timezone.utc) - timedelta(hours=self._rng.randint(1, 48)),
                source=self._rng.choice(["Company PR", "SEC Filing", "Analyst Note"]),
                headline=f"{symbol}: sample headline #{i + 1} (mock data)",
                summary="Synthetic summary for demonstration only — not real news.",
                relevance=round(self._rng.uniform(0.3, 1.0), 2),
                estimated_behavioral_impact=self._rng.choice(["Supportive", "Conflicting", "Neutral"]),
                confidence=round(self._rng.uniform(0.4, 0.9), 2),
                freshness_hours=round(self._rng.uniform(1, 48), 1),
                source_reliability=round(self._rng.uniform(0.5, 0.95), 2),
            ))
        return items


class MockCorporateEventsProvider(CorporateEventsProvider):
    def __init__(self, seed: int = 19) -> None:
        self._rng = random.Random(seed)

    async def get_sec_filings(self, symbol: str) -> List[SECFiling]:
        if self._rng.random() < 0.4:
            return []
        return [SECFiling(
            timestamp=datetime.now(timezone.utc) - timedelta(days=self._rng.randint(1, 60)),
            filing_type=self._rng.choice(["10-K", "10-Q", "8-K"]),
            headline=f"{symbol}: sample filing headline (mock data)",
        )]

    async def get_earnings_events(self, symbol: str) -> List[EarningsEvent]:
        if self._rng.random() < 0.5:
            return []
        eps_est = round(self._rng.uniform(-0.5, 2.0), 2)
        eps_act = round(eps_est + self._rng.uniform(-0.3, 0.3), 2)
        return [EarningsEvent(
            timestamp=datetime.now(timezone.utc) - timedelta(days=self._rng.randint(0, 90)),
            eps_actual=eps_act, eps_estimate=eps_est,
            surprise_pct=round((eps_act - eps_est) / abs(eps_est) * 100.0, 1) if eps_est else None,
            reaction_pct=round(self._rng.uniform(-15, 15), 1),
        )]

    async def get_insider_transactions(self, symbol: str) -> List[InsiderTransaction]:
        if self._rng.random() < 0.6:
            return []
        return [InsiderTransaction(
            timestamp=datetime.now(timezone.utc) - timedelta(days=self._rng.randint(1, 30)),
            insider_role=self._rng.choice(["CEO", "CFO", "Director", "10% Owner"]),
            transaction_type=self._rng.choice(["Buy", "Sell"]),
            shares=round(self._rng.uniform(1000, 50000)),
            value_estimate=round(self._rng.uniform(10_000, 2_000_000), 2),
        )]

    async def get_analyst_revisions(self, symbol: str) -> List[AnalystRevision]:
        if self._rng.random() < 0.5:
            return []
        return [AnalystRevision(
            timestamp=datetime.now(timezone.utc) - timedelta(days=self._rng.randint(1, 14)),
            firm=self._rng.choice(["Sample Capital", "Mock & Co.", "Synthetic Partners"]),
            action=self._rng.choice(["Upgrade", "Downgrade", "Initiate", "Reiterate"]),
            price_target=round(self._rng.uniform(5, 60), 2),
        )]


class MockHistoricalStatsProvider(HistoricalStatsProvider):
    def __init__(self, seed: int = 17) -> None:
        self._rng = random.Random(seed)

    async def get_historical_stats(self, symbol: str, condition_key: str) -> Optional[HistoricalStats]:
        occurrences = self._rng.randint(0, 40)
        if occurrences == 0:
            return HistoricalStats(occurrences=0)
        win_rate = round(self._rng.uniform(0.3, 0.7), 3)
        return HistoricalStats(
            occurrences=occurrences, win_rate=win_rate, loss_rate=round(1.0 - win_rate, 3),
            avg_r=round(self._rng.uniform(-0.3, 1.2), 2), median_r=round(self._rng.uniform(-0.2, 1.0), 2),
            profit_factor=round(self._rng.uniform(0.7, 2.2), 2), avg_hold_bars=round(self._rng.uniform(3, 40), 1),
            max_drawdown=round(self._rng.uniform(0.5, 3.0), 2), mfe=round(self._rng.uniform(0.5, 3.0), 2),
            mae=round(self._rng.uniform(0.3, 2.0), 2),
            confidence_interval_95=(max(0.0, round(win_rate - 0.15, 3)), min(1.0, round(win_rate + 0.15, 3))),
        )


class MockSentimentProvider(SentimentProvider):
    def __init__(self, seed: int = 29) -> None:
        self._rng = random.Random(seed)

    async def classify_text(self, text: str) -> Tuple[str, float]:
        return self._rng.choice(["Positive", "Negative", "Neutral"]), round(self._rng.uniform(0.4, 0.9), 2)
