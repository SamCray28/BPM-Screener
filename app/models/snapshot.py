"""Raw per-symbol input data models. Providers populate these; engines
consume them. Extended from the bpm-screener prototype with
halt_status (from the Market Data Provider requirements) and a Bar/
TimeframeSeries pair for the Multi-Timeframe Engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple


@dataclass
class MarketData:
    symbol: str
    exchange: str
    last_price: float
    volume: float
    avg_daily_volume: float
    avg_daily_dollar_volume: float
    timestamp: Optional[datetime] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    spread: Optional[float] = None
    relative_volume: Optional[float] = None
    vwap: Optional[float] = None
    atr: Optional[float] = None
    daily_range: Optional[float] = None
    premarket_change_pct: Optional[float] = None
    afterhours_change_pct: Optional[float] = None
    gap_pct: Optional[float] = None
    float_shares: Optional[float] = None
    shares_outstanding: Optional[float] = None
    market_cap: Optional[float] = None
    halt_status: Optional[str] = None  # "Trading" | "Halted" | "Limit Up" | "Limit Down" etc.
    is_leveraged_product: bool = False
    is_otc_or_pink_sheet: bool = False
    is_bankrupt: bool = False


@dataclass
class BehavioralData:
    """Mirrors BPM Pine telemetry exactly (BPM_v3.0.1.pine section 17 /
    the bpm-python receiver's TelemetryIn). Pine remains the sole source
    of truth for behavior; nothing here recomputes BO/MC/state."""

    confirmed_state: str
    confirmed_direction: str
    bo_status: str
    mc_status: str
    pressure_efficiency: float
    acceptance_status: str
    bes_scenario: str
    active_bo_price: Optional[float] = None
    active_mc_price: Optional[float] = None
    forecast_bias: Optional[str] = None
    bars_in_confirmed_state: Optional[int] = None
    recent_transition_count: Optional[int] = None


@dataclass
class NewsItem:
    timestamp: datetime
    source: str
    headline: str
    summary: str
    relevance: float
    estimated_behavioral_impact: str  # "Supportive" | "Conflicting" | "Neutral"
    confidence: float
    freshness_hours: Optional[float] = None
    source_reliability: Optional[float] = None  # 0-1, provider-assessed


@dataclass
class SECFiling:
    timestamp: datetime
    filing_type: str
    headline: str
    url: Optional[str] = None


@dataclass
class EarningsEvent:
    timestamp: datetime
    eps_actual: Optional[float] = None
    eps_estimate: Optional[float] = None
    surprise_pct: Optional[float] = None
    reaction_pct: Optional[float] = None


@dataclass
class InsiderTransaction:
    """`transaction_type` uses literal SEC Form 4 terminology ("Buy"/
    "Sell") because that's what the filing says. Never place this
    verbatim into API-facing text — use describe_insider_transaction()."""

    timestamp: datetime
    insider_role: str
    transaction_type: str
    shares: Optional[float] = None
    value_estimate: Optional[float] = None


def describe_insider_transaction(txn: InsiderTransaction) -> str:
    action = "an acquisition" if txn.transaction_type.strip().lower() == "buy" else "a disposition"
    return f"{txn.insider_role} disclosed {action} of shares (Form 4, {txn.timestamp.date().isoformat()})."


@dataclass
class AnalystRevision:
    timestamp: datetime
    firm: str
    action: str  # "Upgrade" | "Downgrade" | "Initiate" | "Reiterate"
    price_target: Optional[float] = None


@dataclass
class HistoricalStats:
    occurrences: int
    win_rate: Optional[float] = None
    loss_rate: Optional[float] = None
    avg_r: Optional[float] = None
    median_r: Optional[float] = None
    profit_factor: Optional[float] = None
    avg_hold_bars: Optional[float] = None
    max_drawdown: Optional[float] = None
    mfe: Optional[float] = None
    mae: Optional[float] = None
    confidence_interval_95: Optional[Tuple[float, float]] = None


@dataclass
class Bar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class TimeframeSeries:
    """Bar history for one timeframe, used by the Multi-Timeframe Engine.
    `bars` is expected oldest-first."""

    timeframe: str  # "1", "5", "15", "60", "240", "D"
    bars: List[Bar] = field(default_factory=list)


@dataclass
class MultiTimeframeSnapshot:
    symbol: str
    series_by_timeframe: Dict[str, TimeframeSeries] = field(default_factory=dict)


@dataclass
class SymbolSnapshot:
    market: MarketData
    behavioral: BehavioralData
    news: List[NewsItem] = field(default_factory=list)
    historical: Optional[HistoricalStats] = None
    multi_timeframe: Optional[MultiTimeframeSnapshot] = None
