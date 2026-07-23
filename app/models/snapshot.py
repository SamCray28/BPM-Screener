"""Raw per-symbol input data. These are what a real provider implementation
(see app/providers/base.py) is responsible for populating — nothing in
this module talks to a live feed itself.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple


@dataclass
class MarketData:
    symbol: str
    exchange: str
    last_price: float
    volume: float
    avg_daily_volume: float
    avg_daily_dollar_volume: float
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
    is_leveraged_product: bool = False
    is_otc_or_pink_sheet: bool = False


@dataclass
class BehavioralData:
    """Mirrors the BPM Pine/telemetry fields (see BPM_v3.0.1.pine section
    17 and the bpm-python receiver's TelemetryIn model). This engine
    consumes behavior — it never recomputes BO/MC/state itself. Pine
    stays the single source of truth, same rule as the Python receiver.

    The three trailing optional fields (forecast_bias,
    bars_in_confirmed_state, recent_transition_count) are NOT part of
    Pine's current telemetry payload — they're what a real Behavioral
    Database (app/db/) would supply by tracking history across
    snapshots. When absent, the Behavior Score's sub-factors that need
    them fall back to neutral-low values with reduced confidence
    rather than guessing (see app/engines/behavioral.py)."""

    confirmed_state: str
    confirmed_direction: str
    bo_status: str
    mc_status: str
    pressure_efficiency: float
    acceptance_status: str
    bes_scenario: str
    active_bo_price: Optional[float] = None
    active_mc_price: Optional[float] = None
    forecast_bias: Optional[str] = None            # e.g. "Continuation Bias" — from Pine section 13
    bars_in_confirmed_state: Optional[int] = None  # requires Behavioral Database history
    recent_transition_count: Optional[int] = None  # requires Behavioral Database history


@dataclass
class SECFiling:
    timestamp: datetime
    filing_type: str      # e.g. "10-K", "10-Q", "8-K", "4"
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
    """Mirrors SEC Form 4 categories directly: `transaction_type` is
    genuinely "Buy" or "Sell" as a matter of filing terminology (an
    insider acquisition or disposition of shares). This is raw ingested
    data, not screener output — never pass transaction_type verbatim
    into a RankedSymbol text field, or the no-directional-language
    safeguard will (correctly) reject it as if it were a trading
    instruction. Use describe_insider_transaction() below instead."""

    timestamp: datetime
    insider_role: str
    transaction_type: str  # "Buy" | "Sell" — SEC Form 4 terminology, see docstring
    shares: Optional[float] = None
    value_estimate: Optional[float] = None


def describe_insider_transaction(txn: InsiderTransaction) -> str:
    """Neutral-language description safe to place in screener output —
    avoids the literal words "buy"/"sell" so this can flow into a
    RankedSymbol text field without tripping (or needing to bypass)
    the no-directional-language safeguard."""
    action = "an acquisition" if txn.transaction_type.strip().lower() == "buy" else "a disposition"
    return f"{txn.insider_role} disclosed {action} of shares (Form 4, {txn.timestamp.date().isoformat()})."


@dataclass
class AnalystRevision:
    timestamp: datetime
    firm: str
    action: str  # "Upgrade" | "Downgrade" | "Initiate" | "Reiterate"
    price_target: Optional[float] = None


@dataclass
class NewsItem:
    timestamp: datetime
    source: str
    headline: str
    summary: str
    relevance: float                    # 0-1
    estimated_behavioral_impact: str    # "Supportive" | "Conflicting" | "Neutral"
    confidence: float                   # 0-1


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
class SymbolSnapshot:
    market: MarketData
    behavioral: BehavioralData
    news: List[NewsItem] = field(default_factory=list)
    historical: Optional[HistoricalStats] = None
