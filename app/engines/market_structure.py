from __future__ import annotations

from app.models.evidence import EvidenceFactor, ScoreExplanation
from app.models.snapshot import MarketData


def score_market_structure(md: MarketData) -> ScoreExplanation:
    spread_pct = (md.spread / md.last_price * 100.0) if md.spread and md.last_price else None
    spread_score = 100.0 if spread_pct is None else max(0.0, 100.0 - spread_pct * 500.0)

    rvol_score = 0.0 if md.relative_volume is None else min(100.0, md.relative_volume * 30.0)

    range_pct = (md.daily_range / md.last_price * 100.0) if md.daily_range and md.last_price else 0.0
    range_score = min(100.0, range_pct * 12.0)

    vwap_score = 50.0
    if md.vwap and md.last_price:
        vwap_dev_pct = abs(md.last_price - md.vwap) / md.vwap * 100.0
        vwap_score = max(0.0, 100.0 - vwap_dev_pct * 20.0)

    gap_score = 0.0 if md.gap_pct is None else min(100.0, abs(md.gap_pct) * 10.0)

    factors = [
        EvidenceFactor("Spread Quality", round(spread_score, 1), 0.25,
                        "Tighter bid/ask spread relative to price implies lower execution friction.",
                        "Market Microstructure"),
        EvidenceFactor("Relative Volume", round(rvol_score, 1), 0.30,
                        "Elevated participation relative to the security's own baseline.",
                        "Market Microstructure"),
        EvidenceFactor("Range Expansion", round(range_score, 1), 0.20,
                        "Daily range as a percentage of price — a proxy for volatility regime.",
                        "Auction Market Theory"),
        EvidenceFactor("VWAP Relationship", round(vwap_score, 1), 0.15,
                        "Proximity to VWAP as a same-session fair-value reference.",
                        "Auction Market Theory"),
        EvidenceFactor("Gap Quality", round(gap_score, 1), 0.10,
                        "Magnitude of the open-to-prior-close gap.",
                        "Market Microstructure"),
    ]
    value = sum(f.value * f.weight for f in factors)
    confidence = 0.9 if (md.spread is not None and md.relative_volume is not None and md.vwap is not None) else 0.55

    return ScoreExplanation(
        score_name="Market Structure Score",
        value=round(value, 1),
        confidence=round(confidence, 2),
        methodology=(
            "Weighted combination of spread quality, relative volume, range "
            "expansion, VWAP relationship, and gap quality computed from the "
            "current market data snapshot."
        ),
        contributing_factors=factors,
    )
