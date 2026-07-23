from __future__ import annotations

from typing import List

from app.models.evidence import EvidenceFactor, ScoreExplanation
from app.models.snapshot import NewsItem

_IMPACT_MAP = {"Supportive": 100.0, "Neutral": 50.0, "Conflicting": 10.0}


def score_sentiment(news: List[NewsItem]) -> ScoreExplanation:
    if not news:
        factors = [
            EvidenceFactor("News Volume", 0.0, 1.0, "No qualifying news items found for this symbol.",
                            "News Engine")
        ]
        return ScoreExplanation(
            score_name="News Impact Score",
            value=0.0,
            confidence=0.2,
            methodology="No news items available; score defaults to neutral-low with low confidence.",
            contributing_factors=factors,
        )

    weighted_sum = 0.0
    weight_total = 0.0
    factors = []
    for item in news:
        impact_val = _IMPACT_MAP.get(item.estimated_behavioral_impact, 50.0)
        w = item.relevance * item.confidence
        weighted_sum += impact_val * w
        weight_total += w
        factors.append(
            EvidenceFactor(
                item.headline, impact_val, round(w, 3),
                f"{item.source} @ {item.timestamp.isoformat()} — impact assessed as "
                f"'{item.estimated_behavioral_impact}' (relevance {item.relevance:.2f}, "
                f"confidence {item.confidence:.2f}).",
                "News Engine",
            )
        )

    value = weighted_sum / weight_total if weight_total > 0 else 50.0
    confidence = min(0.9, weight_total / max(1, len(news)))

    return ScoreExplanation(
        score_name="News Impact Score",
        value=round(value, 1),
        confidence=round(confidence, 2),
        methodology=(
            "Relevance- and confidence-weighted average of each news item's "
            "estimated behavioral impact. News supports the behavioral "
            "assessment; it never overrides it."
        ),
        contributing_factors=factors,
    )
