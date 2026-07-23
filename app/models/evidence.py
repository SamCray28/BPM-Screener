"""Explainability primitives — Rule 2 (Explainability) and Rule 3
(Research Foundation) from the BIS spec.

Every score the screener displays must be backed by one of these
objects, and ScoreExplanation refuses to construct itself (raises
ValueError) if it can't actually explain the number it's holding. That
is the enforcement mechanism for "if the system cannot explain a
score, it must not display it" — it's a hard constructor invariant,
not a convention engines are trusted to follow.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class EvidenceFactor:
    name: str
    value: float
    weight: float
    description: str
    source: str  # which research field / engine this factor came from
    research_key: Optional[str] = None  # looks up a ResearchCard in app/research.py


@dataclass(frozen=True)
class ScoreExplanation:
    score_name: str
    value: float                 # 0-100
    confidence: float            # 0-1: how much evidence supports `value`
    methodology: str
    contributing_factors: List[EvidenceFactor]
    sample_size: Optional[int] = None
    historical_support: Optional[str] = None
    # Rule 3: metrics original to BPM (not drawn from an established
    # field) must say so rather than being presented as established science.
    is_original_to_bpm: bool = False

    def __post_init__(self) -> None:
        if not (0.0 <= self.value <= 100.0):
            raise ValueError(f"{self.score_name}: value must be within 0-100, got {self.value}")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"{self.score_name}: confidence must be within 0-1, got {self.confidence}")
        if not self.contributing_factors:
            raise ValueError(
                f"{self.score_name}: a score with zero contributing factors cannot be "
                f"explained and must not be displayed (Rule 2)."
            )
        if not self.methodology or not self.methodology.strip():
            raise ValueError(f"{self.score_name}: methodology description is required (Rule 2).")

    def factor_weight_sum(self) -> float:
        return sum(f.weight for f in self.contributing_factors)
