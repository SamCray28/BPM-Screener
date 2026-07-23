from __future__ import annotations

from typing import List

from app.models.evidence import EvidenceFactor, ScoreExplanation
from app.models.snapshot import NewsItem

_IMPACT_MAP = {"Supportive": 100.0, "Neutral": 50.0, "Conflicting": 10.0}


def score_news(news: List[NewsItem]) -> ScoreExplanation:
    if not news:
        factors = [EvidenceFactor("News Volume", 0.0, 1.0, "No qualifying news items found for this symbol.",
                                   "News Engine", research_key="News Score")]
        return ScoreExplanation(
            score_name="News Score", value=0.0, confidence=0.2,
            methodology="No news items available; defaults to neutral-low with low confidence.",
            contributing_factors=factors,
        )

    weighted_sum = 0.0
    weight_total = 0.0
    factors = []
    for item in news:
        impact_val = _IMPACT_MAP.get(item.estimated_behavioral_impact, 50.0)
        reliability = item.source_reliability if item.source_reliability is not None else 0.6
        w = item.relevance * item.confidence * reliability
        weighted_sum += impact_val * w
        weight_total += w
        freshness_note = f", {item.freshness_hours:.1f}h old" if item.freshness_hours is not None else ""
        factors.append(EvidenceFactor(
            item.headline, impact_val, round(w, 3),
            f"{item.source} — impact '{item.estimated_behavioral_impact}' "
            f"(relevance {item.relevance:.2f}, confidence {item.confidence:.2f}, "
            f"reliability {reliability:.2f}{freshness_note}).",
            "News Engine", research_key="News Score",
        ))

    value = weighted_sum / weight_total if weight_total > 0 else 50.0
    confidence = min(0.9, weight_total / max(1, len(news)))

    return ScoreExplanation(
        score_name="News Score",
        value=round(value, 1),
        confidence=round(confidence, 2),
        methodology="Relevance-, confidence-, and source-reliability-weighted average of estimated behavioral impact across recent news items.",
        contributing_factors=factors,
    )
