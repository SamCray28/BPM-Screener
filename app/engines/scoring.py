from __future__ import annotations

from app.engines.weights import OpportunityWeights
from app.models.evidence import EvidenceFactor, ScoreExplanation


def combine_opportunity_score(
    behavior: ScoreExplanation,
    structure: ScoreExplanation,
    liquidity: ScoreExplanation,
    historical: ScoreExplanation,
    trend: ScoreExplanation,
    news: ScoreExplanation,
    weights: OpportunityWeights,
) -> ScoreExplanation:
    w = weights.normalized()
    components = [
        (behavior, w.behavior), (structure, w.structure), (liquidity, w.liquidity),
        (historical, w.historical), (trend, w.trend), (news, w.news),
    ]
    value = sum(s.value * weight for s, weight in components)
    weighted_conf = sum(s.confidence * weight for s, weight in components)
    min_conf = min(s.confidence for s, _ in components)
    confidence = weighted_conf * 0.7 + min_conf * 0.3

    factors = [
        EvidenceFactor(s.score_name, s.value, round(weight, 3),
                        f"Contributed at weight {weight:.2f} (own confidence {s.confidence:.2f}).",
                        "Ranking Engine", research_key="Behavioral Opportunity Score")
        for s, weight in components
    ]

    return ScoreExplanation(
        score_name="Behavioral Opportunity Score",
        value=round(value, 1),
        confidence=round(min(1.0, confidence), 2),
        methodology=(
            "Weighted blend of Behavior, Structure, Liquidity, Historical, "
            "Trend, and News scores. Overall confidence blends weighted-"
            "average component confidence with the single lowest component "
            "confidence, so no component can mask another's weak evidence."
        ),
        contributing_factors=factors,
        is_original_to_bpm=True,
    )
