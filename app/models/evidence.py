"""Explainability primitives. A ScoreExplanation cannot be constructed
without contributing factors and a methodology string — an unexplained
score is not a representable state in this system, not just a
convention engines are trusted to follow."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class EvidenceFactor:
    name: str
    value: float
    weight: float
    description: str
    source: str
    research_key: Optional[str] = None


@dataclass(frozen=True)
class ScoreExplanation:
    score_name: str
    value: float
    confidence: float
    methodology: str
    contributing_factors: List[EvidenceFactor]
    sample_size: Optional[int] = None
    historical_support: Optional[str] = None
    is_original_to_bpm: bool = False

    def __post_init__(self) -> None:
        if not (0.0 <= self.value <= 100.0):
            raise ValueError(f"{self.score_name}: value must be within 0-100, got {self.value}")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"{self.score_name}: confidence must be within 0-1, got {self.confidence}")
        if not self.contributing_factors:
            raise ValueError(f"{self.score_name}: a score with zero contributing factors cannot be displayed.")
        if not self.methodology or not self.methodology.strip():
            raise ValueError(f"{self.score_name}: methodology description is required.")

    def factor_weight_sum(self) -> float:
        return sum(f.weight for f in self.contributing_factors)
