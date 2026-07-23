from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class UniverseConfig:
    max_share_price: float = 50.0
    allowed_exchanges: List[str] = field(default_factory=lambda: ["NYSE", "NASDAQ", "AMEX"])
    min_avg_daily_volume: float = 300_000.0
    min_avg_daily_dollar_volume: float = 5_000_000.0
    min_relative_volume: float = 1.0
    exclude_leveraged_products: bool = True


@dataclass
class HistoricalConfig:
    # "No probability should be displayed below a configurable minimum
    # sample threshold" — this is that threshold.
    min_sample_size: int = 20


@dataclass
class ScoringWeights:
    behavioral: float = 0.35
    market_structure: float = 0.20
    historical: float = 0.20
    trend: float = 0.10
    sentiment: float = 0.15

    def normalized(self) -> "ScoringWeights":
        total = self.behavioral + self.market_structure + self.historical + self.trend + self.sentiment
        if total <= 0:
            raise ValueError("ScoringWeights must sum to a positive value.")
        return ScoringWeights(
            behavioral=self.behavioral / total,
            market_structure=self.market_structure / total,
            historical=self.historical / total,
            trend=self.trend / total,
            sentiment=self.sentiment / total,
        )
