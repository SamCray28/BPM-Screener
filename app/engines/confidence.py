from __future__ import annotations

from typing import List

from app.models.evidence import EvidenceFactor, ScoreExplanation


def score_confidence(component_scores: List[ScoreExplanation]) -> ScoreExplanation:
    """Not a component of the Behavioral Opportunity Score — a
    description OF it. A high Confidence Score means the evidence
    behind the ranking is solid; it says nothing about whether the
    opportunity itself is favorable."""
    factors = [
        EvidenceFactor(s.score_name, round(s.confidence * 100.0, 1), round(1.0 / len(component_scores), 3),
                        f"{s.score_name} reported confidence {s.confidence:.2f}.",
                        "Confidence Engine", research_key="Confidence Score")
        for s in component_scores
    ]
    avg_confidence = sum(s.confidence for s in component_scores) / len(component_scores)
    min_confidence = min(s.confidence for s in component_scores)
    # By construction, cannot exceed the weakest component — see the
    # Research Card's confidence_notes.
    value = (avg_confidence * 0.6 + min_confidence * 0.4) * 100.0

    return ScoreExplanation(
        score_name="Confidence Score",
        value=round(value, 1),
        confidence=round(min_confidence, 2),
        methodology="Blend of average component confidence and the single lowest component confidence across all scores contributing to this symbol's ranking.",
        contributing_factors=factors,
        is_original_to_bpm=True,
    )
