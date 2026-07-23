from __future__ import annotations

from app.models.evidence import EvidenceFactor, ScoreExplanation
from app.models.snapshot import MarketData


def score_liquidity(md: MarketData) -> ScoreExplanation:
    dollar_vol_score = min(100.0, (md.avg_daily_dollar_volume / 20_000_000.0) * 100.0)
    share_vol_score = min(100.0, (md.avg_daily_volume / 3_000_000.0) * 100.0)

    float_score = 50.0
    if md.float_shares:
        # Smaller floats move more per dollar of participation — this is
        # treated as a liquidity *characteristic*, not inherently good or bad.
        float_score = max(0.0, min(100.0, 100.0 - (md.float_shares / 100_000_000.0) * 100.0))

    factors = [
        EvidenceFactor("Average Dollar Volume", round(dollar_vol_score, 1), 0.45,
                        "Average daily dollar volume relative to a $20M reference level.",
                        "Market Microstructure"),
        EvidenceFactor("Average Share Volume", round(share_vol_score, 1), 0.35,
                        "Average daily share volume relative to a 3M-share reference level.",
                        "Market Microstructure"),
        EvidenceFactor("Float Characteristic", round(float_score, 1), 0.20,
                        "Free float size, which shapes how much participation is needed to move price.",
                        "Market Microstructure"),
    ]
    value = sum(f.value * f.weight for f in factors)
    confidence = 0.9 if md.float_shares else 0.6

    return ScoreExplanation(
        score_name="Liquidity Score",
        value=round(value, 1),
        confidence=round(confidence, 2),
        methodology="Weighted combination of average dollar volume, average share volume, and float size.",
        contributing_factors=factors,
    )
