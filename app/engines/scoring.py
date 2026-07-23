from __future__ import annotations

from app.config import ScoringWeights
from app.models.evidence import EvidenceFactor, ScoreExplanation


def combine_overall_score(
    behavior: ScoreExplanation,
    market_structure: ScoreExplanation,
    historical: ScoreExplanation,
    trend: ScoreExplanation,
    sentiment: ScoreExplanation,
    weights: ScoringWeights,
) -> ScoreExplanation:
    w = weights.normalized()
    components = [
        (behavior, w.behavioral),
        (market_structure, w.market_structure),
        (historical, w.historical),
        (trend, w.trend),
        (sentiment, w.sentiment),
    ]
    value = sum(s.value * weight for s, weight in components)

    # Overall confidence is a blend of the weighted-average component
    # confidence and the single lowest component confidence, so one very
    # confident component can't paper over another's weak evidence.
    weighted_conf = sum(s.confidence * weight for s, weight in components)
    min_conf = min(s.confidence for s, _ in components)
    confidence = weighted_conf * 0.7 + min_conf * 0.3

    factors = [
        EvidenceFactor(
            s.score_name, s.value, round(weight, 3),
            f"Contributed at weight {weight:.2f} (own confidence {s.confidence:.2f}).",
            "Ranking Engine",
        )
        for s, weight in components
    ]

    return ScoreExplanation(
        score_name="Overall Behavioral Opportunity Score",
        value=round(value, 1),
        confidence=round(min(1.0, confidence), 2),
        methodology=(
            "Weighted blend of Behavior, Market Structure, Historical "
            "Confidence, Trend, and News Impact scores. Overall confidence "
            "blends the weighted-average component confidence with the "
            "single lowest component confidence, so no component can mask "
            "another's weak evidence."
        ),
        contributing_factors=factors,
        is_original_to_bpm=True,
    )
