"""Final decision output, shaped to match the Ranking Engine's required
output fields exactly: Rank, Ticker, Behavior Score, Opportunity Score,
Historical Expectancy, Confidence, Behavior State, Acceptance,
Pressure, Trend, Liquidity, Recent News, Estimated Hold, Primary Risks.
No Buy/Sell field exists here by design — see app/safeguards.py."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from app.models.evidence import ScoreExplanation


@dataclass
class RankedSymbol:
    rank: int
    symbol: str
    behavior_score: ScoreExplanation
    opportunity_score: ScoreExplanation
    sub_scores: List[ScoreExplanation]
    historical_expectancy: Optional[str]
    confidence: float
    historical_sample_size: Optional[int]
    behavior_state: str
    acceptance: str
    pressure: float
    trend_summary: str
    liquidity_summary: str
    recent_news: List[str]
    estimated_hold_duration: Optional[str]
    capital_efficiency: Optional[str]
    primary_risks: List[str] = field(default_factory=list)
    reasons_for_ranking: List[str] = field(default_factory=list)
    supporting_evidence: List[str] = field(default_factory=list)
