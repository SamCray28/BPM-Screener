"""The final per-symbol output — deliberately shaped to match the BIS
spec's "Decision Output" list field-for-field. There is no buy/sell/
long/short field on this object because there must never be one; see
app/safeguards.py for the enforcement that keeps it that way.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from app.models.evidence import ScoreExplanation


@dataclass
class RankedSymbol:
    symbol: str
    behavioral_opportunity_rank: int
    overall_score: ScoreExplanation
    sub_scores: List[ScoreExplanation]
    historical_expectancy: Optional[str]
    supporting_evidence: List[str]
    confidence: float
    historical_sample_size: Optional[int]
    capital_efficiency: Optional[str]
    estimated_hold_duration: Optional[str]
    behavioral_context: str
    primary_risks: List[str] = field(default_factory=list)
    reasons_for_ranking: List[str] = field(default_factory=list)
