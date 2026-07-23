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
    exclude_halted: bool = True
    exclude_bankrupt: bool = True


@dataclass
class HistoricalConfig:
    min_sample_size: int = 20  # "No probability may be displayed until statistically valid"


@dataclass
class OpportunityWeights:
    """Weights for the Behavioral Opportunity Score blend. Confidence
    Score and Capital Efficiency Score are reported independently, not
    blended into this — see app/engines/confidence.py and
    app/engines/capital_efficiency.py."""

    behavior: float = 0.30
    structure: float = 0.15
    liquidity: float = 0.15
    historical: float = 0.20
    trend: float = 0.10
    news: float = 0.10

    def normalized(self) -> "OpportunityWeights":
        total = self.behavior + self.structure + self.liquidity + self.historical + self.trend + self.news
        if total <= 0:
            raise ValueError("OpportunityWeights must sum to a positive value.")
        return OpportunityWeights(
            behavior=self.behavior / total, structure=self.structure / total,
            liquidity=self.liquidity / total, historical=self.historical / total,
            trend=self.trend / total, news=self.news / total,
        )
